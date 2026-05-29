from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from src.storage.project_store import ProjectStore

router = APIRouter()

store = ProjectStore()


@router.get("/{project_id}/chapters")
async def list_chapters(
    project_id: str,
    analyzed: Optional[bool] = Query(None, description="是否已分析"),
):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    chapters = store.load_chapters(project_id)

    entities = store.load_entities(project_id)
    analyzed_chapters = set()
    for e in entities:
        src = e.get("source_chapters", [])
        for s in src:
            if isinstance(s, int):
                analyzed_chapters.add(s)
            elif isinstance(s, str) and s.isdigit():
                analyzed_chapters.add(int(s))

    for ch in chapters:
        ch_idx = ch.get("index", ch.get("chapter_number", 0))
        ch["analyzed"] = ch_idx in analyzed_chapters

    if analyzed is not None:
        chapters = [ch for ch in chapters if ch.get("analyzed") == analyzed]

    return {"chapters": chapters, "total": len(chapters)}
