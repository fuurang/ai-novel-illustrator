import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.storage.project_store import ProjectStore
from src.core.image_generator import ImageGenerator
from src.core.face_anchor import FaceAnchorGenerator
from src.models.entity import Entity
from src.models.prompt import Prompt
from src.models.world_bible import WorldBible
from src.render.chatgpt2api_backend import ChatGPT2APIBackend
from src.api.routers.settings import load_config

router = APIRouter()

store = ProjectStore()

_image_tasks: dict = {}


class GenerateRequest(BaseModel):
    """图片生成请求"""
    entity_ids: Optional[list[str]] = None


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


async def _generate_images_for_project(project_id: str, entity_ids: Optional[list[str]] = None):
    """为项目生成图片"""
    config = load_config()

    entities_data = store.load_entities(project_id)
    prompts_data = store.load_prompts(project_id)

    try:
        world_bible_data = store.load_world_bible(project_id)
    except FileNotFoundError:
        world_bible_data = None

    if not entities_data or not prompts_data:
        return {"error": "缺少实体或提示词数据，请先运行流水线"}

    entities = [Entity(**e) for e in entities_data]
    prompts = [Prompt(**p) for p in prompts_data]
    world_bible = WorldBible(**world_bible_data) if world_bible_data else None

    if entity_ids:
        entities = [e for e in entities if e.id in entity_ids]
        prompts = [p for p in prompts if p.entity_id in entity_ids]

    project_dir = store.get_project_dir(project_id)
    output_dir = str(project_dir / "images")
    face_anchor_dir = str(project_dir / "images" / "face_anchors")

    generator = _build_image_generator(config)

    results = await generator.generate_all(
        entities=entities,
        prompts=prompts,
        world_bible=world_bible or WorldBible(),
        face_anchor_dir=face_anchor_dir,
        output_dir=output_dir,
    )

    return results


async def _generate_single_entity_image(project_id: str, entity_id: str):
    """为单个实体生成图片"""
    config = load_config()

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
        return {"error": f"实体不存在: {entity_id}"}

    prompt_data = None
    for p in prompts_data:
        if p.get("entity_id") == entity_id:
            prompt_data = p
            break

    if not prompt_data:
        return {"error": f"实体 {entity_id} 没有对应的提示词"}

    entity = Entity(**entity_data)
    prompt = Prompt(**prompt_data)
    world_bible = WorldBible(**world_bible_data) if world_bible_data else None

    project_dir = store.get_project_dir(project_id)
    output_dir = str(project_dir / "images")
    face_anchor_dir = str(project_dir / "images" / "face_anchors")

    generator = _build_image_generator(config)

    from src.models.entity import EntityType

    if entity.type == EntityType.CHARACTER:
        face_anchor_path = str(Path(face_anchor_dir) / f"{entity.id}.png")
        if Path(face_anchor_path).exists():
            result = await generator.generate_character(
                entity, prompt, face_anchor_path, output_dir
            )
        else:
            result = await generator.generate_scene(entity, prompt, output_dir=output_dir)
    elif entity.type == EntityType.SCENE:
        result = await generator.generate_scene(entity, prompt, output_dir=output_dir)
    elif entity.type == EntityType.ITEM:
        result = await generator.generate_item(entity, prompt, output_dir=output_dir)
    else:
        return {"error": f"不支持的实体类型: {entity.type}"}

    return {"entity_id": entity_id, "image_path": result}


@router.post("/{project_id}/generate")
async def generate_images(project_id: str, request: GenerateRequest = None):
    """批量生成图片"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entity_ids = request.entity_ids if request else None

    task = asyncio.create_task(_generate_images_for_project(project_id, entity_ids))
    _image_tasks[f"{project_id}_batch"] = task

    return {"message": "图片生成已启动", "project_id": project_id}


@router.post("/{project_id}/generate/{entity_id}")
async def generate_entity_image(project_id: str, entity_id: str):
    """生成单个实体图片"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    try:
        result = await _generate_single_entity_image(project_id, entity_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成失败: {str(e)}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/{project_id}/images")
async def list_images(project_id: str):
    """获取所有图片信息"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    project_dir = store.get_project_dir(project_id)
    images_dir = project_dir / "images"

    images = []
    if images_dir.exists():
        for image_path in images_dir.rglob("*.png"):
            relative = image_path.relative_to(project_dir)
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

            images.append({
                "path": f"/output/{project_id}/{str(relative).replace(chr(92), '/')}",
                "filename": image_path.name,
                "category": category,
                "entity_id": entity_id,
            })

    return {"images": images, "total": len(images)}
