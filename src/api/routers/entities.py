from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.storage.project_store import ProjectStore
from src.api.image_paths import candidate_image_paths, image_url

router = APIRouter()

store = ProjectStore()


def _entity_image_url(project_id: str, entity: dict) -> Optional[str]:
    locked_path = entity.get("locked_image_path")
    if entity.get("image_locked") and locked_path:
        locked_image_path = store.get_project_dir(project_id) / locked_path
        if locked_image_path.exists():
            return image_url(project_id, locked_image_path)

    category_dirs = {
        "character": "characters",
        "scene": "scenes",
        "item": "items",
        "creature": "characters",
    }
    image_dir = category_dirs.get(entity.get("type", ""))
    if not image_dir:
        return None

    entity_id = entity.get("id", "")
    candidates = candidate_image_paths(project_id, image_dir, f"{entity_id}.png")
    if entity.get("type") in {"character", "creature"}:
        candidates.extend(candidate_image_paths(project_id, "scenes", f"{entity_id}.png"))

    image_path = next((path for path in candidates if path.exists()), None)
    if image_path is None:
        return None

    return image_url(project_id, image_path)


def _attach_image_url(project_id: str, entity: dict) -> dict:
    entity = dict(entity)
    image_url = _entity_image_url(project_id, entity)
    if image_url:
        entity["image_url"] = image_url
        entity["image_status"] = "completed"
    if entity.get("image_locked") and image_url:
        entity["locked_image_url"] = image_url
    return entity


def _prompt_by_entity_id(project_id: str) -> dict[str, dict]:
    prompts = store.load_prompts(project_id)
    result = {}
    for prompt in prompts:
        entity_id = prompt.get("entity_id")
        if entity_id and entity_id not in result:
            result[entity_id] = prompt
    return result


def _attach_prompt(project_id: str, entity: dict, prompt_map: Optional[dict[str, dict]] = None) -> dict:
    entity = dict(entity)
    prompt_map = prompt_map if prompt_map is not None else _prompt_by_entity_id(project_id)
    prompt = prompt_map.get(entity.get("id", ""))
    if prompt:
        entity["drawing_prompt"] = prompt.get("chinese_prompt", "")
        entity["negative_prompt"] = prompt.get("negative_prompt", "")
        entity["prompt_id"] = prompt.get("id", "")
        entity["prompt_created_at"] = prompt.get("created_at", "")
    return entity


class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    attributes: Optional[dict] = None
    aliases: Optional[list[str]] = None


class EntityBulkDeleteRequest(BaseModel):
    entity_ids: list[str]


class AppearanceUpdateRequest(BaseModel):
    chapter: int
    appearance_note: Optional[str] = None
    clothing_override: Optional[str] = None


def _delete_entities_from_store(project_id: str, entity_ids: list[str]) -> dict:
    ids = {entity_id for entity_id in entity_ids if entity_id}
    if not ids:
        return {
            "deleted_entity_ids": [],
            "deleted_prompt_count": 0,
            "missing_entity_ids": [],
        }

    entities = store.load_entities(project_id)
    existing_ids = {entity.get("id") for entity in entities}
    deleted_ids = [entity.get("id") for entity in entities if entity.get("id") in ids]
    missing_ids = sorted(ids - existing_ids)

    remaining_entities = [entity for entity in entities if entity.get("id") not in ids]
    store.save_entities(project_id, remaining_entities)

    prompts = store.load_prompts(project_id)
    remaining_prompts = [prompt for prompt in prompts if prompt.get("entity_id") not in ids]
    deleted_prompt_count = len(prompts) - len(remaining_prompts)
    if deleted_prompt_count:
        store.save_prompts(project_id, remaining_prompts)
        store.save_prompts_md(project_id, remaining_prompts, "prompts.md")

    return {
        "deleted_entity_ids": deleted_ids,
        "deleted_prompt_count": deleted_prompt_count,
        "missing_entity_ids": missing_ids,
    }


@router.get("/{project_id}/entities")
async def list_entities(
    project_id: str,
    type: Optional[str] = Query(None, description="实体类型筛选: character/scene/item/creature"),
    chapter: Optional[int] = Query(None, description="按章节筛选"),
):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entities = store.load_entities(project_id)

    if type:
        entities = [e for e in entities if e.get("type") == type]

    if chapter is not None:
        filtered = []
        for e in entities:
            source_quotes = e.get("source_quotes", [])
            for sq in source_quotes:
                sq_ch = sq if isinstance(sq, int) else sq.get("chapter", 0) if isinstance(sq, dict) else 0
                if sq_ch == chapter:
                    filtered.append(e)
                    break
            else:
                source_chapters = e.get("source_chapters", [])
                if chapter in [s if isinstance(s, int) else int(s) for s in source_chapters if isinstance(s, (int, str)) and (isinstance(s, int) or s.isdigit())]:
                    filtered.append(e)
                else:
                    chapter_appearances = e.get("chapter_appearances", [])
                    for ca in chapter_appearances:
                        ca_ch = ca if isinstance(ca, int) else ca.get("chapter", 0) if isinstance(ca, dict) else 0
                        if ca_ch == chapter:
                            filtered.append(e)
                            break
        entities = filtered

    prompt_map = _prompt_by_entity_id(project_id)
    entities = [_attach_prompt(project_id, _attach_image_url(project_id, entity), prompt_map) for entity in entities]

    return {"entities": entities, "total": len(entities)}


@router.get("/{project_id}/entities/{entity_id}")
async def get_entity(project_id: str, entity_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entities = store.load_entities(project_id)

    for entity in entities:
        if entity.get("id") == entity_id:
            entity.setdefault("chapter_appearances", [])
            entity.setdefault("chapter_range", "")
            entity.setdefault("chapter_images", {})
            return _attach_prompt(project_id, _attach_image_url(project_id, entity))

    raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")


@router.put("/{project_id}/entities/{entity_id}")
async def update_entity(project_id: str, entity_id: str, request: EntityUpdateRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entities = store.load_entities(project_id)

    target_idx = None
    for i, entity in enumerate(entities):
        if entity.get("id") == entity_id:
            target_idx = i
            break

    if target_idx is None:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")

    entity = entities[target_idx]

    if request.name is not None:
        entity["name"] = request.name
    if request.aliases is not None:
        entity["aliases"] = request.aliases
    if request.attributes is not None:
        entity["attributes"] = request.attributes

    entities[target_idx] = entity
    store.save_entities(project_id, entities)

    return {"message": "实体更新成功", "entity": entity}


@router.delete("/{project_id}/entities/{entity_id}")
async def delete_entity(project_id: str, entity_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    result = _delete_entities_from_store(project_id, [entity_id])
    if not result["deleted_entity_ids"]:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")

    return {
        "message": "出图对象已删除",
        "entity_id": entity_id,
        "deleted_prompt_count": result["deleted_prompt_count"],
    }


@router.post("/{project_id}/entities/bulk-delete")
async def bulk_delete_entities(project_id: str, request: EntityBulkDeleteRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    result = _delete_entities_from_store(project_id, request.entity_ids)
    deleted_count = len(result["deleted_entity_ids"])
    return {
        "message": f"已删除 {deleted_count} 个出图对象",
        "deleted_count": deleted_count,
        **result,
    }


@router.put("/{project_id}/entities/{entity_id}/appearance")
async def update_entity_appearance(project_id: str, entity_id: str, request: AppearanceUpdateRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entities = store.load_entities(project_id)

    target_idx = None
    for i, entity in enumerate(entities):
        if entity.get("id") == entity_id:
            target_idx = i
            break

    if target_idx is None:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")

    entity = entities[target_idx]
    chapter_appearances = entity.get("chapter_appearances", [])

    found = False
    for i, ca in enumerate(chapter_appearances):
        ca_ch = ca if isinstance(ca, int) else ca.get("chapter", 0) if isinstance(ca, dict) else 0
        if ca_ch == request.chapter:
            if isinstance(ca, dict):
                if request.appearance_note is not None:
                    ca["appearance_note"] = request.appearance_note
                if request.clothing_override is not None:
                    ca["clothing_override"] = request.clothing_override
                chapter_appearances[i] = ca
            found = True
            break

    if not found:
        new_appearance = {
            "chapter": request.chapter,
            "context": "",
            "appearance_note": request.appearance_note or "",
            "clothing_override": request.clothing_override or "",
            "source_quote": "",
        }
        chapter_appearances.append(new_appearance)

    entity["chapter_appearances"] = chapter_appearances
    entities[target_idx] = entity
    store.save_entities(project_id, entities)

    return {"message": "章节外观更新成功", "entity": entity}
