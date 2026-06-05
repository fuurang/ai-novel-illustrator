import asyncio
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.storage.project_store import ProjectStore
from src.core.image_generator import ImageGenerator
from src.core.face_anchor import FaceAnchorGenerator
from src.models.entity import Entity
from src.models.prompt import Prompt
from src.models.world_bible import WorldBible
from src.render.chatgpt2api_backend import ChatGPT2APIBackend
from src.api.routers.settings import load_config
from src.api.image_paths import (
    LEGACY_IMAGE_OUTPUT_ROOT,
    candidate_image_paths,
    get_project_images_dir,
    get_project_output_dir,
    image_url,
)

router = APIRouter()

store = ProjectStore()

_image_tasks: dict = {}


class GenerateRequest(BaseModel):
    entity_ids: Optional[list[str]] = None
    chapter: Optional[int] = None
    skip_locked: bool = True


class LockImageRequest(BaseModel):
    locked: bool = True


class DeleteImageRequest(BaseModel):
    path: str


def _build_image_generator(config: dict) -> ImageGenerator:
    image_config = config.get("image", {})
    chatgpt2api_config = image_config.get("chatgpt2api", {})
    backend_config = {
        "base_url": chatgpt2api_config.get("base_url", ""),
        "api_key": chatgpt2api_config.get("api_key", ""),
        "model": chatgpt2api_config.get("model", "gpt-image-2"),
    }
    backend = ChatGPT2APIBackend(backend_config)
    return ImageGenerator(backend, config)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_project_image_path(project_id: str, image_ref: str) -> Optional[Path]:
    if not image_ref:
        return None

    parsed_path = urlparse(image_ref).path if "://" in image_ref else image_ref
    parsed_path = unquote(parsed_path)
    project_root = get_project_output_dir(project_id).resolve()
    legacy_root = (LEGACY_IMAGE_OUTPUT_ROOT / project_id).resolve()
    output_prefix = f"/output/{project_id}/"
    legacy_prefix = f"/legacy-output/{project_id}/"

    if parsed_path.startswith(output_prefix):
        image_path = (project_root / parsed_path[len(output_prefix):]).resolve()
    elif parsed_path.startswith(legacy_prefix):
        image_path = (legacy_root / parsed_path[len(legacy_prefix):]).resolve()
    else:
        raw_path = Path(parsed_path)
        if raw_path.is_absolute():
            image_path = raw_path.resolve()
        else:
            image_path = (project_root / parsed_path.lstrip("/\\")).resolve()

    if _is_relative_to(image_path, project_root) or _is_relative_to(image_path, legacy_root):
        return image_path
    return None


def _stored_image_path_candidates(project_id: str, value: str) -> list[Path]:
    if not value:
        return []

    candidates: list[Path] = []
    resolved = _resolve_project_image_path(project_id, value)
    if resolved:
        candidates.append(resolved)

    raw_path = Path(value)
    if raw_path.is_absolute():
        candidates.append(raw_path.resolve())
    else:
        candidates.extend(
            [
                raw_path.resolve(),
                (store.get_project_dir(project_id) / value).resolve(),
                (get_project_output_dir(project_id) / value).resolve(),
            ]
        )

    unique_candidates = []
    for path in candidates:
        if path not in unique_candidates:
            unique_candidates.append(path)
    return unique_candidates


def _entity_image_path(project_id: str, entity: dict) -> Optional[Path]:
    locked_path = entity.get("locked_image_path")
    if entity.get("image_locked") and locked_path:
        locked_image_path = store.get_project_dir(project_id) / locked_path
        if locked_image_path.exists():
            return locked_image_path

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

    return next((path for path in candidates if path.exists()), None)


def _clear_deleted_image_references(project_id: str, deleted_path: Path) -> dict:
    entities_data = store.load_entities(project_id)
    deleted_path = deleted_path.resolve()
    changed = False
    unlocked_entities: list[str] = []
    cleaned_chapter_refs = 0

    for entity in entities_data:
        locked_path = entity.get("locked_image_path", "")
        if locked_path:
            if any(path == deleted_path for path in _stored_image_path_candidates(project_id, locked_path)):
                entity["image_locked"] = False
                entity.pop("locked_image_path", None)
                unlocked_entities.append(entity.get("id", ""))
                changed = True

        chapter_images = entity.get("chapter_images", {})
        if isinstance(chapter_images, dict):
            next_chapter_images = {}
            for chapter, image_ref in chapter_images.items():
                if isinstance(image_ref, str) and any(
                    path == deleted_path for path in _stored_image_path_candidates(project_id, image_ref)
                ):
                    cleaned_chapter_refs += 1
                    changed = True
                    continue
                next_chapter_images[chapter] = image_ref
            if next_chapter_images != chapter_images:
                entity["chapter_images"] = next_chapter_images

    if changed:
        store.save_entities(project_id, entities_data)

    return {
        "unlocked_entities": [entity_id for entity_id in unlocked_entities if entity_id],
        "cleaned_chapter_refs": cleaned_chapter_refs,
    }


def _delete_project_image(project_id: str, image_ref: str) -> dict:
    image_path = _resolve_project_image_path(project_id, image_ref)
    if image_path is None:
        return {"error": "图片路径无效，不能删除项目目录外的文件"}

    if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return {"error": "仅支持删除图片文件"}

    if not image_path.exists() or not image_path.is_file():
        return {"error": "图片文件不存在"}

    deleted_url = image_url(project_id, image_path)
    image_path.unlink()
    cleanup = _clear_deleted_image_references(project_id, image_path)

    return {
        "message": "图片已删除",
        "path": deleted_url,
        **cleanup,
    }


def _lock_entity_image(project_id: str, entity_id: str, locked: bool) -> dict:
    entities_data = store.load_entities(project_id)
    target_idx = None
    for index, entity in enumerate(entities_data):
        if entity.get("id") == entity_id:
            target_idx = index
            break

    if target_idx is None:
        return {"error": f"出图对象不存在: {entity_id}"}

    entity = entities_data[target_idx]

    if not locked:
        entity["image_locked"] = False
        entities_data[target_idx] = entity
        store.save_entities(project_id, entities_data)
        current_path = _entity_image_path(project_id, entity)
        return {
            "entity_id": entity_id,
            "image_locked": False,
            "image_url": image_url(project_id, current_path) if current_path else None,
        }

    source_path = _entity_image_path(project_id, entity)
    if source_path is None:
        return {"error": "当前对象还没有可保存的图片"}

    locked_dir = get_project_images_dir(project_id) / "locked"
    locked_dir.mkdir(parents=True, exist_ok=True)
    locked_path = locked_dir / f"{entity_id}.png"
    if source_path.resolve() != locked_path.resolve():
        shutil.copy2(source_path, locked_path)

    relative_locked_path = locked_path.relative_to(store.get_project_dir(project_id))
    entity["image_locked"] = True
    entity["locked_image_path"] = str(relative_locked_path).replace("\\", "/")
    entities_data[target_idx] = entity
    store.save_entities(project_id, entities_data)

    return {
        "entity_id": entity_id,
        "image_locked": True,
        "locked_image_path": entity["locked_image_path"],
        "locked_image_url": image_url(project_id, locked_path),
        "image_url": image_url(project_id, locked_path),
    }


async def _generate_images_for_project(
    project_id: str,
    entity_ids: Optional[list[str]] = None,
    chapter: Optional[int] = None,
    skip_locked: bool = True,
):
    config = load_config()
    image_config = config.get("image", {})
    if not image_config.get("enabled", False):
        return {"error": "生图功能未启用，请先在设置中开启 image.enabled"}
    if image_config.get("backend") != "chatgpt2api":
        return {"error": f"当前仅支持 chatgpt2api 生图后端，当前配置为 {image_config.get('backend')}"}
    if not image_config.get("chatgpt2api", {}).get("api_key"):
        return {"error": "生图后端 API Key 为空，请先在设置中配置"}

    entities_data = store.load_entities(project_id)
    prompts_data = store.load_prompts(project_id)

    try:
        world_bible_data = store.load_world_bible(project_id)
    except FileNotFoundError:
        world_bible_data = None

    if not entities_data:
        return {"error": "缺少出图对象，请先到 AI 工作台执行“识别出图对象”"}
    if not prompts_data:
        return {"error": "缺少绘图指令，请先在 AI 工作台生成角色、场景或物品的绘图指令"}

    entities = [Entity(**e) for e in entities_data]
    prompts = [Prompt(**p) for p in prompts_data]
    world_bible = WorldBible(**world_bible_data) if world_bible_data else None

    if entity_ids:
        entities = [e for e in entities if e.id in entity_ids]
        prompts = [p for p in prompts if p.entity_id in entity_ids]

    if skip_locked:
        locked_entity_ids = {
            e.get("id")
            for e in entities_data
            if e.get("image_locked") and e.get("locked_image_path")
        }
        if locked_entity_ids:
            entities = [e for e in entities if e.id not in locked_entity_ids]
            prompts = [p for p in prompts if p.entity_id not in locked_entity_ids]

    if chapter is not None:
        chapter_entity_ids = set()
        for e in entities:
            for sq in e.source_quotes:
                if sq.chapter == chapter:
                    chapter_entity_ids.add(e.id)
                    break
            else:
                for ca in e.chapter_appearances:
                    if ca.chapter == chapter:
                        chapter_entity_ids.add(e.id)
                        break
        entities = [e for e in entities if e.id in chapter_entity_ids]
        prompts = [p for p in prompts if p.entity_id in chapter_entity_ids]

    output_dir = str(get_project_images_dir(project_id))
    face_anchor_dir = str(get_project_images_dir(project_id) / "face_anchors")

    generator = _build_image_generator(config)

    results = await generator.generate_all(
        entities=entities,
        prompts=prompts,
        world_bible=world_bible or WorldBible(),
        face_anchor_dir=face_anchor_dir,
        output_dir=output_dir,
    )

    if chapter is not None:
        entities_data = store.load_entities(project_id)
        for e_data in entities_data:
            if e_data.get("id") in chapter_entity_ids:
                chapter_images = e_data.get("chapter_images", {})
                if isinstance(results, dict):
                    for key, val in results.items():
                        if isinstance(val, str):
                            chapter_images[str(chapter)] = val
                        elif isinstance(val, dict) and "path" in val:
                            chapter_images[str(chapter)] = val["path"]
                e_data["chapter_images"] = chapter_images
        store.save_entities(project_id, entities_data)

    return results


async def _generate_single_entity_image(project_id: str, entity_id: str, chapter: Optional[int] = None):
    config = load_config()
    image_config = config.get("image", {})
    if not image_config.get("enabled", False):
        return {"error": "生图功能未启用，请先在设置中开启 image.enabled"}
    if image_config.get("backend") != "chatgpt2api":
        return {"error": f"当前仅支持 chatgpt2api 生图后端，当前配置为 {image_config.get('backend')}"}
    if not image_config.get("chatgpt2api", {}).get("api_key"):
        return {"error": "生图后端 API Key 为空，请先在设置中配置"}

    entities_data = store.load_entities(project_id)
    prompts_data = store.load_prompts(project_id)

    try:
        world_bible_data = store.load_world_bible(project_id)
    except FileNotFoundError:
        world_bible_data = None

    entity_data = None
    for e in entities_data:
        if e.get("id") == entity_id:
            entity_data = e
            break

    if not entity_data:
        return {"error": f"出图对象不存在: {entity_id}"}

    if entity_data.get("image_locked") and entity_data.get("locked_image_path"):
        return {"error": "当前图片已保存锁定，请先取消保存后再重抽"}

    prompt_data = None
    for p in prompts_data:
        if p.get("entity_id") == entity_id:
            prompt_data = p
            break

    if not prompt_data:
        return {"error": f"出图对象 {entity_id} 没有对应的绘图指令"}

    entity = Entity(**entity_data)
    prompt = Prompt(**prompt_data)
    world_bible = WorldBible(**world_bible_data) if world_bible_data else None

    output_dir = str(get_project_images_dir(project_id))
    face_anchor_dir = str(get_project_images_dir(project_id) / "face_anchors")

    generator = _build_image_generator(config)

    from src.models.entity import EntityType

    if entity.type == EntityType.CHARACTER:
        face_anchor_path = str(Path(face_anchor_dir) / f"{entity.id}.png")
        if Path(face_anchor_path).exists():
            result = await generator.generate_character(
                entity, prompt, face_anchor_path, output_dir
            )
        else:
            result = await generator.generate_character_without_face(entity, prompt, output_dir)
    elif entity.type == EntityType.SCENE:
        result = await generator.generate_scene(entity, prompt, output_dir=output_dir)
    elif entity.type == EntityType.ITEM:
        result = await generator.generate_item(entity, prompt, output_dir=output_dir)
    else:
        return {"error": f"不支持的实体类型: {entity.type}"}

    if chapter is not None:
        for i, e in enumerate(entities_data):
            if e.get("id") == entity_id:
                chapter_images = e.get("chapter_images", {})
                if isinstance(result, str):
                    chapter_images[str(chapter)] = result
                elif isinstance(result, dict) and "path" in result:
                    chapter_images[str(chapter)] = result["path"]
                entities_data[i]["chapter_images"] = chapter_images
                break
        store.save_entities(project_id, entities_data)

    image_path = Path(result) if isinstance(result, str) else None
    image_url_value = image_url(project_id, image_path) if image_path and image_path.exists() else None

    return {"entity_id": entity_id, "image_path": result, "image_url": image_url_value, "chapter": chapter}


@router.post("/{project_id}/generate")
async def generate_images(project_id: str, request: GenerateRequest = None):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entity_ids = request.entity_ids if request else None
    chapter = request.chapter if request else None
    skip_locked = request.skip_locked if request else True

    try:
        result = await _generate_images_for_project(project_id, entity_ids, chapter, skip_locked)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    if isinstance(result, dict) and result.get("errors") and not (
        result.get("characters") or result.get("scenes") or result.get("items")
    ):
        raise HTTPException(status_code=502, detail="；".join(result["errors"][:3]))

    return {"message": "图片生成完成", "project_id": project_id, "chapter": chapter, "result": result}


@router.post("/{project_id}/generate/{entity_id}")
async def generate_entity_image(
    project_id: str,
    entity_id: str,
    chapter: Optional[int] = Query(None, description="关联章节号"),
):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    try:
        result = await _generate_single_entity_image(project_id, entity_id, chapter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/{project_id}/images/{entity_id}/lock")
async def lock_entity_image(project_id: str, entity_id: str, request: LockImageRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    try:
        result = _lock_entity_image(project_id, entity_id, request.locked)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片保存状态更新失败: {str(e)}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.delete("/{project_id}/images")
async def delete_image(project_id: str, request: DeleteImageRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    try:
        result = _delete_project_image(project_id, request.path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片删除失败: {str(e)}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/{project_id}/images")
async def list_images(
    project_id: str,
    chapter: Optional[int] = Query(None, description="按章节筛选"),
):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    images_dir = get_project_images_dir(project_id)

    entities_data = store.load_entities(project_id)
    entity_chapter_map: dict[str, list[int]] = {}
    for e in entities_data:
        eid = e.get("id", "")
        chapters = set()
        for sq in e.get("source_quotes", []):
            sq_ch = sq if isinstance(sq, int) else sq.get("chapter", 0) if isinstance(sq, dict) else 0
            if sq_ch:
                chapters.add(sq_ch)
        for ca in e.get("chapter_appearances", []):
            ca_ch = ca if isinstance(ca, int) else ca.get("chapter", 0) if isinstance(ca, dict) else 0
            if ca_ch:
                chapters.add(ca_ch)
        for ch_str, img_path in e.get("chapter_images", {}).items():
            if ch_str.isdigit():
                chapters.add(int(ch_str))
        entity_chapter_map[eid] = list(chapters)

    images = []
    if images_dir.exists():
        for image_path in images_dir.rglob("*.png"):
            relative = image_path.relative_to(get_project_output_dir(project_id))
            parts = relative.parts
            entity_id = None
            category = "other"

            if len(parts) >= 3:
                if "characters" in parts:
                    category = "character"
                elif "scenes" in parts:
                    category = "scene"
                elif "items" in parts:
                    category = "item"
                elif "face_anchors" in parts:
                    category = "face_anchor"

                stem = image_path.stem
                if stem and not stem.startswith("."):
                    entity_id = stem.replace("_variation", "").replace("_v2", "")

            image_chapters = []
            if entity_id and entity_id in entity_chapter_map:
                image_chapters = entity_chapter_map[entity_id]

            image_info = {
                "path": image_url(project_id, image_path),
                "filename": image_path.name,
                "category": category,
                "entity_id": entity_id,
                "chapters": image_chapters,
            }

            if chapter is not None:
                if chapter in image_chapters:
                    images.append(image_info)
            else:
                images.append(image_info)

    return {"images": images, "total": len(images)}
