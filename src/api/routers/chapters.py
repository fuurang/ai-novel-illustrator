from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import json
from pathlib import Path

from src.storage.project_store import ProjectStore

router = APIRouter()

store = ProjectStore()


class SceneGroupRequest(BaseModel):
    name: str
    chapter_range: str
    description: str


class SceneGroupUpdateRequest(BaseModel):
    groups: list[dict]


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
        ch_idx = ch.get("index", ch.get("chapter_number", ch.get("number", 0)))
        ch["analyzed"] = ch_idx in analyzed_chapters

    if analyzed is not None:
        chapters = [ch for ch in chapters if ch.get("analyzed") == analyzed]

    for ch in chapters:
        ch_idx = ch.get("index", ch.get("chapter_number", ch.get("number", 0)))
        ch.setdefault("entity_ids", [])
        ch.setdefault("image_ids", [])
        ch.setdefault("summary", "")

        if not ch.get("entity_ids"):
            matched = []
            for e in entities:
                source_quotes = e.get("source_quotes", [])
                for sq in source_quotes:
                    sq_ch = sq if isinstance(sq, int) else sq.get("chapter", 0) if isinstance(sq, dict) else 0
                    if sq_ch == ch_idx:
                        matched.append(e.get("id", ""))
                        break
                source_chapters = e.get("source_chapters", [])
                if ch_idx in [s if isinstance(s, int) else int(s) for s in source_chapters if isinstance(s, (int, str)) and (isinstance(s, int) or s.isdigit())]:
                    if e.get("id", "") not in matched:
                        matched.append(e.get("id", ""))
            ch["entity_ids"] = matched

    return {"chapters": chapters, "total": len(chapters)}


@router.get("/{project_id}/chapters/{chapter_number}")
async def get_chapter(project_id: str, chapter_number: int):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    chapters = store.load_chapters(project_id)

    chapter = None
    for ch in chapters:
        ch_idx = ch.get("index", ch.get("chapter_number", ch.get("number", 0)))
        if ch_idx == chapter_number:
            chapter = ch
            break

    if chapter is None:
        raise HTTPException(status_code=404, detail=f"章节不存在: {chapter_number}")

    entities = store.load_entities(project_id)
    matched_entities = []
    for e in entities:
        source_quotes = e.get("source_quotes", [])
        for sq in source_quotes:
            sq_ch = sq if isinstance(sq, int) else sq.get("chapter", 0) if isinstance(sq, dict) else 0
            if sq_ch == chapter_number:
                matched_entities.append(e)
                break
        else:
            source_chapters = e.get("source_chapters", [])
            if chapter_number in [s if isinstance(s, int) else int(s) for s in source_chapters if isinstance(s, (int, str)) and (isinstance(s, int) or s.isdigit())]:
                matched_entities.append(e)

    images = []
    project_dir = store.get_project_dir(project_id)
    images_dir = project_dir / "images"
    if images_dir.exists():
        for image_path in images_dir.rglob("*.png"):
            relative = image_path.relative_to(project_dir)
            parts = relative.parts
            category = "other"
            entity_id = None

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

            image_info = {
                "path": f"/output/{project_id}/{str(relative).replace(chr(92), '/')}",
                "filename": image_path.name,
                "category": category,
                "entity_id": entity_id,
            }

            if entity_id and entity_id in [e.get("id", "") for e in matched_entities]:
                image_info["chapter"] = chapter_number
                images.append(image_info)

    chapter.setdefault("entity_ids", [e.get("id", "") for e in matched_entities])
    chapter.setdefault("image_ids", [img.get("filename", "") for img in images])
    chapter.setdefault("summary", "")

    return {
        "chapter": chapter,
        "entities": matched_entities,
        "images": images,
    }


def load_scene_groups(project_id: str) -> list[dict]:
    project_dir = store.get_project_dir(project_id)
    scene_groups_file = project_dir / "scene_groups.json"
    if scene_groups_file.exists():
        try:
            with open(scene_groups_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_scene_groups(project_id: str, groups: list[dict]):
    project_dir = store.get_project_dir(project_id)
    scene_groups_file = project_dir / "scene_groups.json"
    with open(scene_groups_file, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)


def parse_chapter_range(range_str: str) -> list[int]:
    chapters = []
    if not range_str:
        return chapters
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                chapters.extend(range(start, end + 1))
            except Exception:
                pass
        else:
            try:
                chapters.append(int(part))
            except Exception:
                pass
    return sorted(list(set(chapters)))


@router.get("/{project_id}/scene-groups")
async def list_scene_groups(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    groups = load_scene_groups(project_id)
    return {"groups": groups, "total": len(groups)}


@router.put("/{project_id}/scene-groups")
async def update_scene_groups(project_id: str, request: SceneGroupUpdateRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    save_scene_groups(project_id, request.groups)
    return {"message": "场景分组更新成功", "groups": request.groups}


@router.post("/{project_id}/scene-groups/auto-detect")
async def auto_detect_scene_groups(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    
    chapters = store.load_chapters(project_id)
    if not chapters:
        return {"groups": [], "total": 0}
    
    entities = store.load_entities(project_id)
    
    groups = []
    
    # 先尝试从已提取的场景实体来分组
    scene_entities = [e for e in entities if e.get("type") == "scene"]
    if scene_entities:
        # 从场景实体的章节范围来分组
        for scene in scene_entities:
            name = scene.get("name", "")
            if not name:
                continue
            
            chapter_range = scene.get("chapter_range", "")
            if chapter_range:
                group = {
                    "id": scene.get("id", ""),
                    "name": name,
                    "chapter_range": chapter_range,
                    "chapters": parse_chapter_range(chapter_range),
                    "description": scene.get("attributes", {}).get("visual_description", "")
                }
                groups.append(group)
    
    # 如果没有场景实体或分组，就按章节间隔自动分组（每5章一组）
    if not groups:
        total_chapters = len(chapters)
        group_size = 5
        for i in range(0, total_chapters, group_size):
            start_chapter = i + 1
            end_chapter = min(i + group_size, total_chapters)
            group = {
                "id": f"group_{i}",
                "name": f"场景区域 {i//group_size + 1}",
                "chapter_range": f"{start_chapter}-{end_chapter}",
                "chapters": list(range(start_chapter, end_chapter + 1)),
                "description": f"第 {start_chapter} 至 {end_chapter} 章的场景"
            }
            groups.append(group)
    
    save_scene_groups(project_id, groups)
    return {"groups": groups, "total": len(groups)}
