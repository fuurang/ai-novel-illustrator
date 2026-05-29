from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.storage.project_store import ProjectStore

router = APIRouter()

store = ProjectStore()


class EntityUpdateRequest(BaseModel):
    """实体更新请求"""
    name: Optional[str] = None
    attributes: Optional[dict] = None
    aliases: Optional[list[str]] = None


@router.get("/{project_id}/entities")
async def list_entities(
    project_id: str,
    type: Optional[str] = Query(None, description="实体类型筛选: character/scene/item/creature"),
):
    """获取实体列表，支持按类型筛选"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entities = store.load_entities(project_id)

    if type:
        entities = [e for e in entities if e.get("type") == type]

    return {"entities": entities, "total": len(entities)}


@router.get("/{project_id}/entities/{entity_id}")
async def get_entity(project_id: str, entity_id: str):
    """获取实体详情"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    entities = store.load_entities(project_id)

    for entity in entities:
        if entity.get("id") == entity_id:
            return entity

    raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")


@router.put("/{project_id}/entities/{entity_id}")
async def update_entity(project_id: str, entity_id: str, request: EntityUpdateRequest):
    """更新实体属性"""
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
