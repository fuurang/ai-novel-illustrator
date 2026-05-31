from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
import json
from pathlib import Path

from src.storage.project_store import ProjectStore
from src.api.image_paths import get_project_images_dir, get_project_output_dir, image_url
from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader

router = APIRouter()

store = ProjectStore()
SCENE_SEGMENT_BATCH_CHAPTERS = 12
SCENE_SEGMENT_MAX_INTERNAL_ROUNDS = 20


class SceneGroupRequest(BaseModel):
    name: str
    chapter_range: str
    description: str


class SceneGroupUpdateRequest(BaseModel):
    groups: list[dict]


class SceneSegmentationRequest(BaseModel):
    start_chapter: Optional[int] = None
    max_chapters: Optional[int] = None
    granularity: str = "medium"


SCENE_GRANULARITY = {
    "fine": {
        "label": "细",
        "instruction": "细粒度：倾向于把地点、目标、冲突或时间状态稍有明显变化的段落拆开；允许只分 1-3 章，适合城市探索、楼层推进、副本小关卡。",
    },
    "medium": {
        "label": "中",
        "instruction": "中粒度：按主要剧情阶段分段；只有主要空间、行动目标、危险来源或阶段状态明显变化时才切换。",
    },
    "coarse": {
        "label": "粗",
        "instruction": "粗粒度：倾向于合并同一大地图/大副本/长行动线中的连续章节；只有进入新的大地图、新副本、新长期目标或世界规则变化时才切换。",
    },
}


def scene_granularity_config(granularity: str, max_chapters: int | None = None) -> dict:
    return dict(SCENE_GRANULARITY.get(granularity, SCENE_GRANULARITY["medium"]))


_llm_adapter = None
_prompt_loader = None


def get_llm_adapter():
    global _llm_adapter, _prompt_loader
    if _llm_adapter is None:
        import yaml
        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        _llm_adapter = LLMAdapter(config)
        _prompt_loader = PromptLoader(config.get('prompts_dir', 'config/prompts'))
    return _llm_adapter, _prompt_loader


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
    images_dir = get_project_images_dir(project_id)
    if images_dir.exists():
        for image_path in images_dir.rglob("*.png"):
            relative = image_path.relative_to(get_project_output_dir(project_id))
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
                "path": image_url(project_id, image_path),
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


def get_chapter_number(chapter: dict, fallback: int = 0) -> int:
    return int(chapter.get("number", chapter.get("chapter_number", chapter.get("index", fallback))) or fallback)


def select_chapters_from_number(chapters: list[dict], start_chapter: int) -> list[dict]:
    return [
        chapter for chapter in chapters
        if get_chapter_number(chapter) >= start_chapter
    ]


def chapter_context(chapters: list[dict]) -> list[dict]:
    return [
        {
            'number': get_chapter_number(chapter, i + 1),
            'title': chapter.get('title', f'第{i + 1}章'),
            'text': chapter.get('text', ''),
        }
        for i, chapter in enumerate(chapters)
    ]


def slice_chapter_batch(chapters: list[dict], offset: int) -> list[dict]:
    return chapters[offset:offset + SCENE_SEGMENT_BATCH_CHAPTERS]


def group_end_chapter(group: dict) -> int:
    chapters = group.get("chapters") or []
    if chapters:
        try:
            return max(int(chapter) for chapter in chapters)
        except Exception:
            pass

    parsed = parse_chapter_range(group.get("chapter_range", ""))
    return max(parsed) if parsed else 0


def group_start_chapter(group: dict) -> int:
    chapters = group.get("chapters") or []
    if chapters:
        try:
            return min(int(chapter) for chapter in chapters)
        except Exception:
            pass

    parsed = parse_chapter_range(group.get("chapter_range", ""))
    return min(parsed) if parsed else 0


def confirmed_scene_groups(groups: list[dict]) -> list[dict]:
    return [
        group for group in groups
        if group.get("source") in {"ai", "manual"}
    ]


def next_scene_start_chapter(chapters: list[dict], groups: list[dict]) -> int:
    chapter_numbers = sorted(
        get_chapter_number(chapter, index + 1)
        for index, chapter in enumerate(chapters)
    )
    if not chapter_numbers:
        return 1

    cursor = chapter_numbers[0]
    for group in sorted(confirmed_scene_groups(groups), key=group_start_chapter):
        start = group_start_chapter(group)
        end = group_end_chapter(group)
        if start <= cursor <= end:
            cursor = end + 1
        elif start > cursor:
            break

    return cursor


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
    
    # 不再按固定章节数生成“假场景”。场景分段必须由 AI 或用户确认产生；
    # 固定 5 章切块会误导后续实体提取和提示词生成。
    if not groups:
        existing_groups = load_scene_groups(project_id)
        return {
            "groups": existing_groups,
            "total": len(existing_groups),
            "message": "未发现可自动转换的场景实体；请使用智能分场景逐段识别。",
        }
    
    save_scene_groups(project_id, groups)
    return {"groups": groups, "total": len(groups)}


@router.post("/{project_id}/scene-groups/segment-one")
async def segment_one_scene(project_id: str, request: SceneSegmentationRequest):
    """智能识别下一个完整场景。"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    chapters = store.load_chapters(project_id)
    if not chapters:
        return {"scene": None, "message": "没有章节数据"}

    project = store.load_project_info(project_id) or {}
    existing_groups = load_scene_groups(project_id)
    start_chapter = request.start_chapter or next_scene_start_chapter(chapters, existing_groups)
    granularity = scene_granularity_config(request.granularity, request.max_chapters)
    last_chapter_number = max(
        get_chapter_number(chapter, index + 1)
        for index, chapter in enumerate(chapters)
    )
    if start_chapter > last_chapter_number:
        return {
            "scene": None,
            "message": "所有章节都已经完成场景分段",
            "start_chapter": start_chapter,
            "next_start_chapter": start_chapter,
        }

    existing_scenes_text = "\n".join([
        f"- {group.get('name', '')}: 第{group.get('chapter_range', '')}章"
        for group in confirmed_scene_groups(existing_groups)
    ]) or "（暂无已确认场景）"

    chapters_to_analyze = select_chapters_from_number(chapters, start_chapter)
    if not chapters_to_analyze:
        return {
            "scene": None,
            "message": "没有更多章节需要分析",
            "start_chapter": start_chapter,
            "next_start_chapter": start_chapter,
        }

    llm_adapter, prompt_loader = get_llm_adapter()
    base_context = {
        "novel_title": project.get('novel_title', project.get('novel_name', project.get('name', '小说'))),
        "start_chapter": start_chapter,
        "granularity_label": granularity["label"],
        "granularity_instruction": granularity["instruction"],
        "existing_scenes": existing_scenes_text,
    }

    try:
        result = {}
        analyzed_chapters = []
        for round_index in range(SCENE_SEGMENT_MAX_INTERNAL_ROUNDS):
            offset = round_index * SCENE_SEGMENT_BATCH_CHAPTERS
            batch = slice_chapter_batch(chapters_to_analyze, offset)
            if not batch:
                break

            analyzed_chapters.extend(batch)
            context = {
                **base_context,
                "last_available_chapter": get_chapter_number(analyzed_chapters[-1]),
                "available_chapter_count": len(chapters_to_analyze),
                "has_more_chapters": offset + len(batch) < len(chapters_to_analyze),
                "chapters": chapter_context(analyzed_chapters),
            }
            system_prompt, prompt = prompt_loader.render('scene_segmentation', context)
            if system_prompt:
                prompt = f"{system_prompt}\n\n{prompt}"
            result = await llm_adapter.generate_json_async(prompt)
            scene_data = result.get('scene', {})
            analysis = result.get('analysis', {})
            if scene_data and (not analysis.get('needs_more_chapters') or not context["has_more_chapters"]):
                break

        scene_data = result.get('scene', {})
        if not scene_data:
            return {
                "scene": None,
                "message": "未识别到完整场景",
                "start_chapter": start_chapter,
                "next_start_chapter": start_chapter,
            }

        analyzed_max = max(
            get_chapter_number(chapter, index + 1)
            for index, chapter in enumerate(analyzed_chapters or chapters_to_analyze)
        )
        start_ch = int(scene_data.get('start_chapter', start_chapter) or start_chapter)
        end_ch = int(scene_data.get('end_chapter', start_chapter) or start_chapter)
        if start_ch != start_chapter:
            start_ch = start_chapter
        if end_ch < start_ch:
            end_ch = start_ch
        if end_ch > analyzed_max:
            end_ch = analyzed_max

        new_group = {
            "id": f"scene_{start_ch}_{end_ch}",
            "name": scene_data.get('name', f'场景 {start_ch}-{end_ch}'),
            "chapter_range": f"{start_ch}-{end_ch}",
            "chapters": list(range(start_ch, end_ch + 1)),
            "description": scene_data.get('description', ''),
            "confidence": scene_data.get('confidence', 0.8),
            "reasoning": result.get('analysis', {}).get('reasoning', '') or result.get('readable_report', ''),
            "granularity": request.granularity,
            "internal_read_rounds": result.get('analysis', {}).get('internal_read_rounds', 1),
            "source": "ai",
        }

        return {
            "scene": new_group,
            "analysis": result.get('analysis', {}),
            "start_chapter": start_chapter,
            "next_start_chapter": end_ch + 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"场景识别失败: {str(e)}")


@router.post("/{project_id}/scene-groups/add")
async def add_scene_group(project_id: str, group: dict):
    """添加一个场景分组（用户确认后调用）"""
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    groups = load_scene_groups(project_id)
    group.setdefault('id', f'scene_{len(groups) + 1}')
    group.setdefault('source', 'manual')
    groups.append(group)
    save_scene_groups(project_id, groups)
    return {"groups": groups, "total": len(groups)}
