from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.storage.project_store import ProjectStore

router = APIRouter()

store = ProjectStore()


class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    attributes: Optional[dict] = None
    aliases: Optional[list[str]] = None


class AppearanceUpdateRequest(BaseModel):
    chapter: int
    appearance_note: Optional[str] = None
    clothing_override: Optional[str] = None


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
            return entity

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
