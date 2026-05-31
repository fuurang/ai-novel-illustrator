import hashlib
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from src.storage.project_store import ProjectStore
from src.api.image_paths import get_project_images_dir

router = APIRouter()

store = ProjectStore()


def _format_project(info: dict) -> dict:
    project_id = info.get("id", "")
    project_dir = store.get_project_dir(project_id)

    entity_stats = {"characters": 0, "scenes": 0, "items": 0}
    entities = store.load_entities(project_id)
    for e in entities:
        etype = e.get("type", "")
        if etype == "character":
            entity_stats["characters"] += 1
        elif etype == "scene":
            entity_stats["scenes"] += 1
        elif etype == "item":
            entity_stats["items"] += 1

    images_dir = get_project_images_dir(project_id)
    image_count = 0
    if images_dir.exists():
        image_count = sum(1 for _ in images_dir.rglob("*.png"))

    has_wb = (project_dir / "data" / "world_bible.json").exists()

    status = "idle"
    if info.get("error"):
        status = "error"
    elif has_wb and len(entities) > 0:
        status = "completed"

    return {
        "id": project_id,
        "name": info.get("name", ""),
        "novel_name": info.get("novel_name", Path(info.get("input_file", "")).stem if info.get("input_file") else ""),
        "status": status,
        "created_at": info.get("created_at", ""),
        "stats": {
            "characters": entity_stats["characters"],
            "scenes": entity_stats["scenes"],
            "items": entity_stats["items"],
            "images": image_count,
        },
    }


@router.get("")
async def list_projects():
    projects = store.list_projects()
    result = []
    for p in projects:
        project_id = p.get("id", "")
        info = store.load_project_info(project_id)
        result.append(_format_project(info))
    return {"projects": result}


@router.post("")
async def create_project(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    project_name = name or Path(file.filename).stem
    project_id = hashlib.md5(f"{file.filename}_{time.time()}".encode()).hexdigest()[:12]

    store.create_project(project_id, project_name)

    project_dir = store.get_project_dir(project_id)
    input_dir = project_dir / "data"
    input_dir.mkdir(parents=True, exist_ok=True)

    file_path = input_dir / file.filename
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    import json
    from datetime import datetime

    project_info = store.load_project_info(project_id)
    project_info["input_file"] = str(file_path)
    project_info["novel_name"] = Path(file.filename).stem
    project_info["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    info_file = project_dir / "project.json"
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(project_info, f, ensure_ascii=False, indent=2)

    return _format_project(project_info)


@router.get("/{project_id}")
async def get_project(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    info = store.load_project_info(project_id)
    return _format_project(info)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    store.delete_project(project_id)
    return {"message": f"项目 {project_id} 已删除"}
