from fastapi import APIRouter, HTTPException

from src.storage.project_store import ProjectStore

router = APIRouter()

store = ProjectStore()


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
