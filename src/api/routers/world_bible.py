from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from src.storage.project_store import ProjectStore

router = APIRouter()

store = ProjectStore()


class WorldBibleUpdate(BaseModel):
    """世界观更新请求"""
    world_bible: Dict[str, Any]


@router.get("/{project_id}/world-bible")
async def get_world_bible(project_id: str):
    """获取世界观"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    try:
        world_bible = store.load_world_bible(project_id)
        return world_bible
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 尚未构建世界观")


@router.put("/{project_id}/world-bible")
async def update_world_bible(project_id: str, request: WorldBibleUpdate):
    """更新世界观"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    
    try:
        store.save_world_bible(project_id, request.world_bible)
        return {"success": True, "message": "世界观已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")
