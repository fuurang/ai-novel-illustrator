import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.routers.settings import load_config
from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader
from src.core.entity_extractor import EntityExtractor
from src.core.entity_merger import EntityMerger
from src.models.chapter import Chapter
from src.models.entity import Entity
from src.models.prompt import Prompt, PromptParameters
from src.models.world_bible import WorldBible
from src.storage.project_store import ProjectStore

router = APIRouter()
store = ProjectStore()


class AiPrepareRequest(BaseModel):
    task: str
    chapter_number: Optional[int] = None
    entity_id: Optional[str] = None
    start_chapter: Optional[int] = None
    max_chapters: Optional[int] = None
    extraction_level: str = "balanced"
    scene_granularity: str = "medium"
    extra_instruction: str = ""
    attachment_refs: List[str] = []
    followup_run_id: Optional[str] = None


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


def _scene_granularity_config(granularity: str, max_chapters: int | None = None) -> Dict[str, Any]:
    return dict(SCENE_GRANULARITY.get(granularity, SCENE_GRANULARITY["medium"]))


class AiRunRequest(AiPrepareRequest):
    apply_result: bool = False
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None


class AiApplyRequest(BaseModel):
    run_id: str


class AiAttachmentContentRequest(BaseModel):
    ref: str


TASKS = [
    {
        "key": "world_bible_analyze",
        "label": "世界观分析",
        "description": "从小说文本中提取世界观框架和视觉证据",
        "needs": ["chapters"],
        "can_apply": True,
    },
    {
        "key": "visual_anchoring",
        "label": "视觉锚定",
        "description": "把世界观框架转换成统一视觉规则",
        "needs": ["world_bible"],
        "can_apply": True,
    },
    {
        "key": "entity_extraction",
        "label": "识别出图对象",
        "description": "从当前场景正文识别需要生图的角色、场景和物品",
        "needs": ["chapter", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "character_attribute",
        "label": "精修角色视觉设定",
        "description": "基于当前场景和已有证据持续补充指定角色的外观、语言动作气质和阶段变化",
        "needs": ["entity", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "scene_attribute",
        "label": "整理场景视觉设定",
        "description": "为指定场景补全环境、氛围和画面规则",
        "needs": ["entity", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "item_attribute",
        "label": "整理物品视觉设定",
        "description": "为指定物品补全形态、材质和辨识细节",
        "needs": ["entity", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "character_prompt",
        "label": "生成角色绘图指令",
        "description": "为指定角色生成可发送给生图 API 的绘图指令",
        "needs": ["entity", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "scene_prompt",
        "label": "生成场景绘图指令",
        "description": "为指定场景生成可发送给生图 API 的绘图指令",
        "needs": ["entity", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "item_prompt",
        "label": "生成物品绘图指令",
        "description": "为指定物品生成可发送给生图 API 的绘图指令",
        "needs": ["entity", "world_bible"],
        "can_apply": True,
    },
    {
        "key": "scene_segmentation",
        "label": "智能分场景",
        "description": "从指定章节开始识别一个完整场景区域",
        "needs": ["chapters"],
        "can_apply": True,
    },
]

ATTACHMENT_LIMIT_CHARS = 30000
SCENE_SEGMENT_BATCH_CHAPTERS = 12
SCENE_SEGMENT_MAX_INTERNAL_ROUNDS = 20


def _get_prompt_loader() -> PromptLoader:
    return PromptLoader()


def _get_llm() -> LLMAdapter:
    return LLMAdapter(load_config())


def _chapter_number(chapter: dict, fallback: int = 0) -> int:
    return int(chapter.get("number", chapter.get("chapter_number", chapter.get("index", fallback))) or fallback)


def _parse_chapter_range(range_str: str) -> List[int]:
    chapters: List[int] = []
    if not range_str:
        return chapters

    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = [int(value.strip()) for value in part.split("-", 1)]
                chapters.extend(range(start, end + 1))
            except Exception:
                continue
        else:
            try:
                chapters.append(int(part))
            except Exception:
                continue

    return sorted(set(chapters))


def _scene_group_end_chapter(group: dict) -> int:
    chapters = group.get("chapters") or []
    if chapters:
        try:
            return max(int(chapter) for chapter in chapters)
        except Exception:
            pass

    parsed = _parse_chapter_range(group.get("chapter_range", ""))
    return max(parsed) if parsed else 0


def _scene_group_start_chapter(group: dict) -> int:
    chapters = group.get("chapters") or []
    if chapters:
        try:
            return min(int(chapter) for chapter in chapters)
        except Exception:
            pass

    parsed = _parse_chapter_range(group.get("chapter_range", ""))
    return min(parsed) if parsed else 0


def _confirmed_scene_groups(groups: List[dict]) -> List[dict]:
    return [
        group for group in groups
        if group.get("source") in {"ai", "manual"}
    ]


def _last_chapter_number(chapters: List[dict]) -> int:
    chapter_numbers = [_chapter_number(chapter, index + 1) for index, chapter in enumerate(chapters)]
    return max(chapter_numbers) if chapter_numbers else 0


def _chapters_from(chapters: List[dict], start_chapter: int) -> List[dict]:
    return [
        chapter for chapter in chapters
        if _chapter_number(chapter) >= start_chapter
    ]


def _chapter_context(chapters: List[dict]) -> List[Dict[str, Any]]:
    return [
        {
            "number": _chapter_number(chapter, index + 1),
            "title": chapter.get("title", f"第{index + 1}章"),
            "text": chapter.get("text", ""),
        }
        for index, chapter in enumerate(chapters)
    ]


def _slice_chapter_batch(chapters: List[dict], offset: int) -> List[dict]:
    return chapters[offset:offset + SCENE_SEGMENT_BATCH_CHAPTERS]


def _load_scene_groups(project_id: str) -> List[Dict[str, Any]]:
    groups_file = store.get_project_dir(project_id) / "scene_groups.json"
    if not groups_file.exists():
        return []
    try:
        with open(groups_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_scene_groups(project_id: str, groups: List[Dict[str, Any]]) -> None:
    groups_file = store.get_project_dir(project_id) / "scene_groups.json"
    with open(groups_file, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)


def _next_scene_start_chapter(chapters: List[dict], groups: List[dict]) -> int:
    chapter_numbers = sorted(_chapter_number(chapter, index + 1) for index, chapter in enumerate(chapters))
    if not chapter_numbers:
        return 1

    cursor = chapter_numbers[0]
    confirmed_groups = _confirmed_scene_groups(groups)
    for group in sorted(confirmed_groups, key=_scene_group_start_chapter):
        start = _scene_group_start_chapter(group)
        end = _scene_group_end_chapter(group)
        if start <= cursor <= end:
            cursor = end + 1
        elif start > cursor:
            break

    return cursor


def _find_chapter(project_id: str, chapter_number: Optional[int]) -> dict:
    chapters = store.load_chapters(project_id)
    if not chapters:
        raise HTTPException(status_code=400, detail="项目还没有章节数据")

    if chapter_number is None:
        return chapters[0]

    for chapter in chapters:
        current = _chapter_number(chapter)
        if current == chapter_number:
            return chapter

    raise HTTPException(status_code=404, detail=f"章节不存在: {chapter_number}")


def _find_entity(project_id: str, entity_id: Optional[str]) -> dict:
    if not entity_id:
        raise HTTPException(status_code=400, detail="该任务需要选择实体")

    for entity in store.load_entities(project_id):
        if entity.get("id") == entity_id:
            return entity

    raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")


def _load_world_bible(project_id: str) -> WorldBible:
    try:
        return WorldBible(**store.load_world_bible(project_id))
    except FileNotFoundError:
        return WorldBible(project_id=project_id)


def _format_quotes(entity: dict) -> str:
    quotes = entity.get("source_quotes", [])
    if not quotes:
        return "（无原文引用）"

    lines = []
    for quote in quotes:
        if isinstance(quote, str):
            lines.append(f"- {quote}")
            continue
        location = quote.get("location") or f"第{quote.get('chapter', 0)}章"
        lines.append(f"- [{location}] {quote.get('text', '')}")

    return "\n".join(lines)


def _format_chapter_appearances(entity: dict) -> str:
    appearances = entity.get("chapter_appearances", [])
    if not appearances:
        return "（暂无章节出场记录）"

    lines = []
    for item in appearances[:120]:
        if not isinstance(item, dict):
            lines.append(f"- {item}")
            continue
        chapter = item.get("chapter", 0)
        context = item.get("context", "")
        appearance_note = item.get("appearance_note", "")
        clothing_override = item.get("clothing_override", "")
        source_quote = item.get("source_quote", "")
        detail_parts = [
            part for part in [
                f"场景/动作: {context}" if context else "",
                f"外观: {appearance_note}" if appearance_note else "",
                f"服饰变化: {clothing_override}" if clothing_override else "",
                f"证据: {source_quote}" if source_quote else "",
            ]
            if part
        ]
        lines.append(f"- 第{chapter}章: " + "；".join(detail_parts))

    return "\n".join(lines)


def _latest_prompt_for_entity(project_id: str, entity_id: str, prompt_type: Optional[str] = None) -> Optional[dict]:
    for prompt in store.load_prompts(project_id):
        if prompt.get("entity_id") != entity_id:
            continue
        if prompt_type and prompt.get("type") != prompt_type:
            continue
        prompt_copy = dict(prompt)
        if prompt_copy.get("chinese_prompt"):
            prompt_copy["chinese_prompt"] = str(prompt_copy["chinese_prompt"])[:3000]
        if prompt_copy.get("negative_prompt"):
            prompt_copy["negative_prompt"] = str(prompt_copy["negative_prompt"])[:1000]
        return prompt_copy
    return None


_EMPTY_TEXT_MARKERS = {
    "",
    "原文未提及",
    "未提及",
    "暂无",
    "不详",
    "不明确",
    "未知",
    "无法判断",
    "无明确证据",
    "没有明确证据",
}


def _is_meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        normalized = text.strip("。；;,.，、：: ")
        if normalized in _EMPTY_TEXT_MARKERS:
            return False
        if normalized in {"无明确原文证据", "证据不足", "原文没有明确提及"}:
            return False
        return True
    if isinstance(value, list):
        return any(_is_meaningful(item) for item in value)
    if isinstance(value, dict):
        return any(_is_meaningful(item) for item in value.values())
    return True


def _dedupe_list(items: List[Any]) -> List[Any]:
    seen = set()
    result = []
    for item in items:
        if not _is_meaningful(item):
            continue
        if isinstance(item, str):
            key = item.strip()
        else:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _merge_attribute_value(existing: Any, incoming: Any) -> Any:
    if not _is_meaningful(incoming):
        return existing
    if not _is_meaningful(existing):
        return incoming
    if isinstance(existing, dict) and isinstance(incoming, dict):
        merged = dict(existing)
        for key, value in incoming.items():
            merged[key] = _merge_attribute_value(merged.get(key), value)
        return merged
    if isinstance(existing, list) and isinstance(incoming, list):
        return _dedupe_list(existing + incoming)
    return incoming


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coerce_chapter(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return 0


def _coerce_source_quote(item: Any) -> Optional[Dict[str, Any]]:
    if isinstance(item, str):
        text = item.strip()
        return {"chapter": 0, "text": text, "location": ""} if text else None
    if not isinstance(item, dict):
        return None

    raw_text = (
        item.get("text")
        or item.get("quote")
        or item.get("source_quote")
        or item.get("evidence")
        or ""
    )
    text = str(raw_text).strip()
    if not text:
        return None

    chapter = _coerce_chapter(item.get("chapter") or item.get("chapter_number"))
    location = item.get("location") or (f"第{chapter}章" if chapter else "")
    return {
        "chapter": chapter,
        "text": text,
        "location": location,
    }


def _source_quote_text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("text") or item.get("quote") or item.get("source_quote") or "").strip()
    return ""


def _merge_source_quotes(entity: dict, parsed: Dict[str, Any]) -> int:
    evidence_updates = parsed.get("evidence_updates", {}) if isinstance(parsed.get("evidence_updates"), dict) else {}
    incoming_items: List[Any] = []
    for key in ["source_quotes", "new_source_quotes", "visual_evidence_quotes"]:
        incoming_items.extend(_as_list(parsed.get(key)))
    incoming_items.extend(_as_list(evidence_updates.get("source_quotes")))

    existing = entity.get("source_quotes", [])
    existing_texts = {_source_quote_text(item) for item in existing if _source_quote_text(item)}
    added = 0
    for item in incoming_items:
        quote = _coerce_source_quote(item)
        if not quote:
            continue
        text = quote["text"]
        if text in existing_texts:
            continue
        existing.append(quote)
        existing_texts.add(text)
        added += 1

    entity["source_quotes"] = existing[:300]
    return added


def _coerce_chapter_appearance(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None

    chapter = _coerce_chapter(item.get("chapter") or item.get("chapter_number") or item.get("start_chapter"))
    context = item.get("context") or item.get("scene") or item.get("event") or item.get("action_context") or ""
    appearance_note = (
        item.get("appearance_note")
        or item.get("appearance")
        or item.get("visual_note")
        or item.get("description")
        or ""
    )
    clothing_override = item.get("clothing_override") or item.get("clothing") or item.get("costume") or ""
    source_quote = item.get("source_quote") or item.get("quote") or item.get("text") or ""

    if not chapter and not any([context, appearance_note, clothing_override, source_quote]):
        return None

    return {
        "chapter": chapter,
        "context": str(context).strip(),
        "appearance_note": str(appearance_note).strip(),
        "clothing_override": str(clothing_override).strip(),
        "source_quote": str(source_quote).strip(),
    }


def _appearance_signature(item: Dict[str, Any]) -> tuple:
    quote = str(item.get("source_quote", "")).strip()
    if quote:
        return (item.get("chapter", 0), quote)
    return (
        item.get("chapter", 0),
        str(item.get("context", "")).strip(),
        str(item.get("appearance_note", "")).strip(),
        str(item.get("clothing_override", "")).strip(),
    )


def _merge_chapter_appearances(entity: dict, parsed: Dict[str, Any]) -> int:
    evidence_updates = parsed.get("evidence_updates", {}) if isinstance(parsed.get("evidence_updates"), dict) else {}
    incoming_items: List[Any] = []
    for key in ["chapter_appearances", "appearance_updates", "stage_appearances"]:
        incoming_items.extend(_as_list(parsed.get(key)))
    incoming_items.extend(_as_list(evidence_updates.get("chapter_appearances")))

    appearances = [
        item for item in entity.get("chapter_appearances", [])
        if isinstance(item, dict)
    ]
    index_by_signature = {
        _appearance_signature(item): idx
        for idx, item in enumerate(appearances)
    }
    added = 0

    for item in incoming_items:
        appearance = _coerce_chapter_appearance(item)
        if not appearance:
            continue
        signature = _appearance_signature(appearance)
        existing_idx = index_by_signature.get(signature)
        if existing_idx is not None:
            current = appearances[existing_idx]
            for key, value in appearance.items():
                if _is_meaningful(value) and not _is_meaningful(current.get(key)):
                    current[key] = value
            appearances[existing_idx] = current
            continue
        appearances.append(appearance)
        index_by_signature[signature] = len(appearances) - 1
        added += 1

    appearances.sort(key=lambda item: _coerce_chapter(item.get("chapter")))
    entity["chapter_appearances"] = appearances[:300]
    return added


def _refresh_entity_chapter_metadata(entity: dict) -> None:
    chapters = set()
    for quote in entity.get("source_quotes", []):
        if isinstance(quote, dict):
            chapter = _coerce_chapter(quote.get("chapter"))
            if chapter:
                chapters.add(chapter)
    for appearance in entity.get("chapter_appearances", []):
        if isinstance(appearance, dict):
            chapter = _coerce_chapter(appearance.get("chapter"))
            if chapter:
                chapters.add(chapter)
    for chapter in entity.get("source_chapters", []):
        chapter_no = _coerce_chapter(chapter)
        if chapter_no:
            chapters.add(chapter_no)

    if not chapters:
        return

    sorted_chapters = sorted(chapters)
    entity["source_chapters"] = sorted_chapters
    current_first = _coerce_chapter(entity.get("first_appearance_chapter"))
    if not current_first or sorted_chapters[0] < current_first:
        entity["first_appearance_chapter"] = sorted_chapters[0]
    entity["chapter_range"] = (
        str(sorted_chapters[0])
        if sorted_chapters[0] == sorted_chapters[-1]
        else f"{sorted_chapters[0]}-{sorted_chapters[-1]}"
    )


def _readable_report_from(parsed: Dict[str, Any]) -> str:
    report = parsed.get("readable_report")
    if isinstance(report, str) and report.strip():
        return report.strip()
    analysis = parsed.get("analysis")
    if isinstance(analysis, dict):
        report = analysis.get("readable_report") or analysis.get("summary")
        if isinstance(report, str) and report.strip():
            return report.strip()
    return ""


def _merge_refinement_notes(
    entity: dict,
    parsed: Dict[str, Any],
    request: AiRunRequest,
    added_quote_count: int,
    added_appearance_count: int,
) -> None:
    attributes = entity.setdefault("attributes", {})
    if not isinstance(attributes, dict):
        attributes = {}
        entity["attributes"] = attributes

    refinement = attributes.setdefault("_refinement", {})
    if not isinstance(refinement, dict):
        refinement = {}
        attributes["_refinement"] = refinement

    now = datetime.now().isoformat()
    report = _readable_report_from(parsed)
    refinement["last_refined_at"] = now
    refinement["last_attachment_refs"] = request.attachment_refs
    refinement["prompt_refresh_required"] = True
    if report:
        refinement["last_report"] = report

    for key in [
        "missing_info",
        "conflicts",
        "uncertainties",
        "revision_suggestions",
        "visual_evidence",
        "speech_action_evidence",
        "stage_changes",
    ]:
        value = parsed.get(key)
        if _is_meaningful(value):
            refinement[key] = value

    history = refinement.get("history", [])
    if not isinstance(history, list):
        history = []
    history.insert(0, {
        "refined_at": now,
        "attachment_refs": request.attachment_refs,
        "added_source_quotes": added_quote_count,
        "added_chapter_appearances": added_appearance_count,
        "summary": report[:500] if report else "",
    })
    refinement["history"] = history[:30]


def _merge_character_attribute_result(entity: dict, parsed: Dict[str, Any], request: AiRunRequest) -> Dict[str, int]:
    incoming_attributes = parsed.get("attributes") or parsed.get("refined_attributes") or {}
    if isinstance(incoming_attributes, dict) and incoming_attributes:
        existing_attributes = entity.get("attributes", {})
        if not isinstance(existing_attributes, dict):
            existing_attributes = {}
        entity["attributes"] = _merge_attribute_value(existing_attributes, incoming_attributes)

    added_quote_count = _merge_source_quotes(entity, parsed)
    added_appearance_count = _merge_chapter_appearances(entity, parsed)
    _refresh_entity_chapter_metadata(entity)
    _merge_refinement_notes(entity, parsed, request, added_quote_count, added_appearance_count)
    return {
        "added_source_quotes": added_quote_count,
        "added_chapter_appearances": added_appearance_count,
    }


def _summarize_world_bible(wb: WorldBible) -> str:
    forbidden = ", ".join(wb.visual_anchoring.forbidden_elements) if wb.visual_anchoring.forbidden_elements else "无"
    return (
        f"类型: {wb.world_framework.genre} | "
        f"子类型: {wb.world_framework.sub_genre} | "
        f"时代: {wb.world_framework.era_setting} | "
        f"力量体系: {wb.world_framework.power_system} | "
        f"用户补充: {wb.user_worldview_text[:1000]} | "
        f"禁止元素: {forbidden}"
    )


def _format_existing_entities(project_id: str) -> str:
    entities = store.load_entities(project_id)
    if not entities:
        return "（无已有出图对象）"

    lines = []
    for entity in entities[:200]:
        aliases = ", ".join(entity.get("aliases", [])) if entity.get("aliases") else "无"
        lines.append(f"- [{entity.get('type', 'unknown')}] {entity.get('name', '')} (别名: {aliases})")

    return "\n".join(lines)


def _append_extra_instruction(user_prompt: str, extra_instruction: str) -> str:
    if not extra_instruction.strip():
        return user_prompt

    return (
        f"{user_prompt}\n\n"
        "【用户本轮补充要求】\n"
        f"{extra_instruction.strip()}\n\n"
        "请优先满足本轮补充要求；如果它与原文证据冲突，请在输出 JSON 的 reasoning、analysis、notes 或相近字段中说明冲突点。"
    )


def _append_visibility_contract(user_prompt: str) -> str:
    return (
        f"{user_prompt}\n\n"
        "【可见依据要求】\n"
        "请不要输出隐藏思维链或逐步内心推理。请输出可供用户检查的简明依据，尽量放在 JSON 的 analysis、reasoning、notes、evidence、conflicts、revision_suggestions 等相近字段中：\n"
        "1. 关键判断依据：每个重要判断对应哪些原文证据或引用材料。\n"
        "2. 不确定点：哪些内容证据不足，不能强行推断。\n"
        "3. 冲突处理：当全局世界观、阶段设定、当前原文冲突时，说明采用了哪个以及原因。\n"
        "4. 可调整建议：如果用户要继续追问，建议优先调整哪些字段。\n"
        "5. 必须输出 readable_report 字段：这是给普通用户直接阅读的完整中文说明，不要写成 JSON 元数据清单。"
        "它需要用自然语言说明本轮生成/修改了什么、采用了哪些关键原文依据、哪里存在冲突或不确定、下一轮可以怎么追问微调。"
        "如果本轮任务仍要求 JSON 输出，请保留原有结构化字段，同时额外加入 readable_report。"
    )


def _find_ai_run(project_id: str, run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not run_id:
        return None
    for run in store.load_ai_runs(project_id):
        if run.get("id") == run_id:
            return run
    return None


def _append_followup_context(user_prompt: str, previous_run: Optional[Dict[str, Any]]) -> str:
    if not previous_run:
        return user_prompt

    previous_payload = {
        "task": previous_run.get("task"),
        "extra_instruction": previous_run.get("extra_instruction", ""),
        "parsed_output": previous_run.get("parsed_output", {}),
        "raw_output_preview": str(previous_run.get("raw_output", ""))[:4000],
    }
    return (
        f"{user_prompt}\n\n"
        "【上一轮结果，供本轮追问/微调使用】\n"
        f"{json.dumps(previous_payload, ensure_ascii=False, indent=2)}\n\n"
        "请基于上一轮结果进行修正，不要无视用户追问；如果沿用上一轮判断，请说明可见依据。"
    )


def _read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="gbk", errors="ignore") as f:
            return f.read()


def _safe_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _attachment_preview_text(value: Any, limit: int = 900) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, indent=2)
    return text[:limit]


def _get_attachment_catalog(project_id: str) -> List[Dict[str, Any]]:
    project = store.load_project_info(project_id)
    project_dir = store.get_project_dir(project_id)
    world_data = _safe_json_file(project_dir / "data" / "world_bible.json", {})
    entities_data = _safe_json_file(project_dir / "data" / "entities.json", [])
    prompts_data = _safe_json_file(project_dir / "prompts" / "prompts.json", [])
    scene_groups = _load_scene_groups(project_id)
    attachments: List[Dict[str, Any]] = []

    input_file = project.get("input_file")
    if input_file:
        attachments.append({
            "ref": "file:input",
            "label": "原始小说文件",
            "kind": "file",
            "description": input_file,
            "summary": "导入的完整小说原文文件，通常只在重建世界观时使用。",
            "preview": _read_text_file(input_file)[:900] if Path(input_file).exists() else "",
        })

    attachments.append({
        "ref": "data:world_bible",
        "label": "世界观数据",
        "kind": "derived",
        "description": "world_bible.json",
        "summary": "全书的题材、时代、末日规则、视觉风格和世界观约束。",
        "preview": _attachment_preview_text({
            "题材": world_data.get("genre", ""),
            "子类型": world_data.get("sub_genre", ""),
            "时代背景": world_data.get("era_setting", ""),
            "科技/力量水平": world_data.get("technology_level", ""),
            "核心概念": world_data.get("key_concepts", []),
            "画面基调": world_data.get("tone_and_mood", ""),
        }),
    })
    attachments.append({
        "ref": "data:entities",
        "label": "出图对象库",
        "kind": "derived",
        "description": "entities.json",
        "summary": f"已经识别过的出图对象库，共 {len(entities_data) if isinstance(entities_data, list) else 0} 个；用于避免重复创建，也用于持续补充已有角色设定。",
        "preview": _attachment_preview_text([
            {
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "chapters": item.get("source_chapters", []),
            }
            for item in (entities_data if isinstance(entities_data, list) else [])[:12]
        ]),
    })
    attachments.append({
        "ref": "data:prompts",
        "label": "提示词数据",
        "kind": "derived",
        "description": "prompts.json",
        "summary": f"已经生成的绘图指令，共 {len(prompts_data) if isinstance(prompts_data, list) else 0} 条；识别出图对象阶段通常不需要。",
        "preview": _attachment_preview_text(prompts_data[:5] if isinstance(prompts_data, list) else prompts_data),
    })
    attachments.append({
        "ref": "data:scene_groups",
        "label": "场景目录",
        "kind": "derived",
        "description": "scene_groups.json",
        "summary": f"全书已确认的场景目录，共 {len(_confirmed_scene_groups(scene_groups))} 个，用于判断当前场景处在全书哪个阶段。",
        "preview": _attachment_preview_text([
            {
                "name": group.get("name", ""),
                "chapter_range": group.get("chapter_range", ""),
                "description": group.get("description", ""),
            }
            for group in _confirmed_scene_groups(scene_groups)[:12]
        ]),
    })

    chapter_map = {
        _chapter_number(chapter): chapter
        for chapter in store.load_chapters(project_id)
    }
    for group in _confirmed_scene_groups(scene_groups):
        chapter_range = group.get("chapter_range", "")
        group_chapters = [
            chapter_map.get(int(chapter))
            for chapter in group.get("chapters", [])
            if str(chapter).isdigit() and chapter_map.get(int(chapter))
        ]
        attachments.append({
            "ref": f"scene:{group.get('id', '')}",
            "label": f"场景：{group.get('name', '未命名场景')}",
            "kind": "scene",
            "description": f"第{chapter_range}章",
            "chapter_range": chapter_range,
            "chapters": group.get("chapters", []),
            "summary": f"当前场景正文引用，覆盖第{chapter_range}章。识别出图对象时主要读取这里。",
            "preview": _attachment_preview_text({
                "场景名称": group.get("name", ""),
                "章节范围": chapter_range,
                "场景说明": group.get("description", ""),
                "章节标题": [
                    f"第{_chapter_number(chapter)}章 {chapter.get('title', '')}"
                    for chapter in group_chapters[:20]
                ],
            }),
        })

    for chapter in store.load_chapters(project_id):
        chapter_number = _chapter_number(chapter)
        attachments.append({
            "ref": f"chapter:{chapter_number}",
            "label": f"第{chapter_number}章",
            "kind": "chapter",
            "description": chapter.get("title", ""),
        })

    return attachments


def _resolve_attachments(project_id: str, refs: List[str]) -> List[Dict[str, str]]:
    if not refs:
        return []

    project = store.load_project_info(project_id)
    project_dir = store.get_project_dir(project_id)
    attachments: List[Dict[str, str]] = []
    chapters = store.load_chapters(project_id)

    for ref in refs:
        try:
            if ref == "file:input":
                path = project.get("input_file")
                if path:
                    content = _read_text_file(path)[:ATTACHMENT_LIMIT_CHARS]
                    attachments.append({
                        "ref": ref,
                        "label": "原始小说文件",
                        "content": content,
                    })
            elif ref == "data:world_bible":
                wb_path = project_dir / "data" / "world_bible.json"
                if wb_path.exists():
                    attachments.append({
                        "ref": ref,
                        "label": "世界观数据",
                        "content": _read_text_file(str(wb_path))[:ATTACHMENT_LIMIT_CHARS],
                    })
            elif ref == "data:entities":
                entity_path = project_dir / "data" / "entities.json"
                if entity_path.exists():
                    attachments.append({
                        "ref": ref,
                        "label": "出图对象库",
                        "content": _read_text_file(str(entity_path))[:ATTACHMENT_LIMIT_CHARS],
                    })
            elif ref == "data:prompts":
                prompt_path = project_dir / "prompts" / "prompts.json"
                if prompt_path.exists():
                    attachments.append({
                        "ref": ref,
                        "label": "提示词数据",
                        "content": _read_text_file(str(prompt_path))[:ATTACHMENT_LIMIT_CHARS],
                    })
            elif ref == "data:scene_groups":
                scene_path = project_dir / "scene_groups.json"
                if scene_path.exists():
                    attachments.append({
                        "ref": ref,
                        "label": "场景目录",
                        "content": _read_text_file(str(scene_path))[:ATTACHMENT_LIMIT_CHARS],
                    })
            elif ref.startswith("scene:"):
                scene_id = ref.split(":", 1)[1]
                scene = next((group for group in _load_scene_groups(project_id) if str(group.get("id", "")) == scene_id), None)
                if scene:
                    chapter_numbers = set(int(chapter) for chapter in scene.get("chapters", []) if str(chapter).isdigit())
                    scene_chapters = [
                        chapter for chapter in chapters
                        if _chapter_number(chapter) in chapter_numbers
                    ]
                    if scene_chapters:
                        content = {
                            "scene": scene,
                            "chapters": scene_chapters,
                        }
                        attachments.append({
                            "ref": ref,
                            "label": f"当前场景正文：{scene.get('name', '未命名场景')}",
                            "content": json.dumps(content, ensure_ascii=False, indent=2)[:ATTACHMENT_LIMIT_CHARS],
                        })
            elif ref.startswith("chapter:"):
                chapter_no = int(ref.split(":", 1)[1])
                for chapter in chapters:
                    current = _chapter_number(chapter)
                    if current == chapter_no:
                        attachments.append({
                            "ref": ref,
                            "label": f"第{chapter_no}章",
                            "content": json.dumps(chapter, ensure_ascii=False, indent=2)[:ATTACHMENT_LIMIT_CHARS],
                        })
                        break
        except Exception:
            continue

    return attachments


def _scene_ref_from_refs(refs: List[str]) -> Optional[str]:
    for ref in refs:
        if ref.startswith("scene:"):
            return ref.split(":", 1)[1]
    return None


def _chapters_for_scene(project_id: str, scene_id: str) -> List[dict]:
    scene = next((group for group in _load_scene_groups(project_id) if str(group.get("id", "")) == scene_id), None)
    if not scene:
        return []
    chapter_numbers = set(int(chapter) for chapter in scene.get("chapters", []) if str(chapter).isdigit())
    return [
        chapter for chapter in store.load_chapters(project_id)
        if _chapter_number(chapter) in chapter_numbers
    ]


def _fallback_chapter_for_request(project_id: str, request: AiPrepareRequest) -> int:
    if request.chapter_number:
        return request.chapter_number
    scene_ref = _scene_ref_from_refs(request.attachment_refs)
    if scene_ref:
        scene_chapters = _chapters_for_scene(project_id, scene_ref)
        if scene_chapters:
            return min(_chapter_number(chapter) for chapter in scene_chapters)
    return 0


def _append_attachments(user_prompt: str, attachments: List[Dict[str, str]]) -> str:
    if not attachments:
        return user_prompt

    blocks = []
    for attachment in attachments:
        blocks.append(
            f"【引用材料：{attachment['label']}】\n{attachment['content']}"
        )

    return f"{user_prompt}\n\n" + "\n\n".join(blocks)


def _append_attachment_refs(user_prompt: str, attachments: List[Dict[str, str]]) -> str:
    if not attachments:
        return user_prompt

    lines = [
        f"- {attachment.get('label', attachment.get('ref', ''))}（{attachment.get('ref', '')}）：执行时由后端自动读取并发送给 API"
        for attachment in attachments
    ]
    return f"{user_prompt}\n\n【已关联文件】\n" + "\n".join(lines)


def _display_context(task: str, context: Dict[str, Any]) -> Dict[str, Any]:
    display = dict(context)

    if task == "world_bible_analyze" and display.get("text_content"):
        display["text_content"] = "【已关联：小说正文片段。点击发送给 AI 时由后端自动读取，不需要在这里展开原文。】"

    if task == "entity_extraction" and display.get("chapter_text"):
        chapter_number = display.get("chapter_number", "")
        display["chapter_text"] = f"【已关联：第{chapter_number}章正文。点击发送给 AI 时由后端自动读取。】"

    if task == "scene_segmentation" and isinstance(display.get("chapters"), list):
        display["chapters"] = [
            {
                **chapter,
                "text": f"【已关联：第{chapter.get('number', '')}章正文。点击发送给 AI 时由后端自动读取。】",
            }
            for chapter in display["chapters"]
        ]

    if task == "character_attribute":
        for field, label in {
            "entity_json": "当前角色完整档案",
            "existing_attributes": "已有角色视觉设定",
            "chapter_appearances": "历史章节出场记录",
            "source_quotes": "已有原文短引用",
            "existing_prompt": "已有绘图指令",
            "world_bible_visual_rules": "世界观角色视觉规则",
        }.items():
            if display.get(field):
                display[field] = f"【已关联：{label}。点击发送给 AI 时由后端自动读取，不需要在这里展开。】"

    long_structured_fields = [
        "existing_entities",
        "world_framework",
        "source_evidence",
        "source_quotes",
        "entity_json",
        "existing_attributes",
        "chapter_appearances",
        "existing_prompt",
        "world_bible_visual_rules",
        "world_bible_visual_anchoring",
        "world_bible_scene_rules",
        "world_bible_item_rules",
    ]
    for field in long_structured_fields:
        value = display.get(field)
        if isinstance(value, str) and len(value) > 1200:
            display[field] = f"【已关联：{field} 项目数据。点击发送给 AI 时由后端自动读取。】"

    return display


def _build_execution_sources(context: Dict[str, Any], attachments: List[Dict[str, str]]) -> List[Dict[str, str]]:
    sources: List[Dict[str, str]] = []

    def add(label: str, content: Any) -> None:
        if content is None:
            return
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2)
        if text.strip():
            sources.append({"label": label, "content": text})

    add("小说正文片段", context.get("text_content"))
    add("章节正文", context.get("chapter_text"))
    add("已有出图对象库", context.get("existing_entities"))
    add("世界观框架数据", context.get("world_framework"))
    add("识别证据数据", context.get("source_evidence"))
    add("当前出图对象完整档案", context.get("entity_json"))
    add("当前角色已有视觉设定", context.get("existing_attributes"))
    add("当前角色历史出场记录", context.get("chapter_appearances"))
    add("当前角色已有绘图指令", context.get("existing_prompt"))
    add("世界观角色视觉规则", context.get("world_bible_visual_rules"))
    add("世界观视觉锚定数据", context.get("world_bible_visual_anchoring"))
    add("场景视觉规则数据", context.get("world_bible_scene_rules"))
    add("物品视觉规则数据", context.get("world_bible_item_rules"))

    chapters = context.get("chapters")
    if isinstance(chapters, list):
        for chapter in chapters:
            if isinstance(chapter, dict):
                number = chapter.get("number", "")
                title = chapter.get("title", "")
                add(f"第{number}章 {title}".strip(), chapter.get("text"))

    for attachment in attachments:
        add(f"关联文件：{attachment.get('label', attachment.get('ref', ''))}", attachment.get("content"))

    return sources


def _append_execution_sources(user_prompt: str, sources: List[Dict[str, str]]) -> str:
    if not sources:
        return user_prompt

    blocks = [
        f"【后端自动读取的关联内容：{source['label']}】\n{source['content']}"
        for source in sources
    ]
    return f"{user_prompt}\n\n【以下内容不会在前端指令框展开，但会随本次 API 请求发送给模型】\n" + "\n\n".join(blocks)


def _source_refs(sources: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    return [
        {
            "label": source.get("label", ""),
            "chars": len(source.get("content", "")),
        }
        for source in sources
    ]


def _public_prepared(prepared: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": prepared["task"],
        "context": prepared["context"],
        "attachments": prepared.get("attachments", []),
        "execution_sources": _source_refs(prepared.get("execution_sources", [])),
        "followup_run": prepared.get("followup_run"),
        "system_prompt": prepared["system_prompt"],
        "user_prompt": prepared["user_prompt"],
    }


def _public_run(run: Dict[str, Any]) -> Dict[str, Any]:
    hidden_keys = {
        "execution_context",
        "execution_attachments",
        "execution_user_prompt",
        "template_execution_user_prompt",
    }
    public = {key: value for key, value in run.items() if key not in hidden_keys}
    if "execution_sources" not in public:
        public["execution_sources"] = _source_refs(_build_execution_sources(
            run.get("execution_context", run.get("context", {})),
            run.get("execution_attachments", []),
        ))
    return public


def _build_world_context(wb: WorldBible, entity_type: str) -> dict:
    context = {
        "visual_anchoring": wb.visual_anchoring.model_dump(),
        "world_framework": wb.world_framework.model_dump(),
        "user_worldview_text": wb.user_worldview_text,
    }

    if entity_type == "character":
        context["character_visual_rules"] = wb.character_visual_rules.model_dump()
    elif entity_type == "scene":
        context["scene_visual_rules"] = wb.scene_visual_rules.model_dump()
    elif entity_type == "item":
        context["item_visual_rules"] = wb.item_visual_rules.model_dump()

    return context


def _prepare_prompt(project_id: str, request: AiPrepareRequest) -> Dict[str, Any]:
    loader = _get_prompt_loader()
    task = request.task
    wb = _load_world_bible(project_id)
    context: Dict[str, Any] = {}

    if task == "world_bible_analyze":
        chapters = store.load_chapters(project_id)
        if not chapters:
            raise HTTPException(status_code=400, detail="项目还没有章节数据")
        project = store.load_project_info(project_id)
        text_content = "\n\n".join([
            chapter.get("text", "") for chapter in chapters[:5]
        ])[:30000]
        context = {
            "novel_title": project.get("novel_name", project.get("name", "")),
            "text_content": text_content,
        }

    elif task == "visual_anchoring":
        project = store.load_project_info(project_id)
        framework = wb.world_framework.model_dump()
        world_data = store.load_world_bible(project_id) if store.project_exists(project_id) else {}
        context = {
            "novel_title": project.get("novel_name", project.get("name", "")),
            "world_framework": json.dumps(framework, ensure_ascii=False),
            "source_evidence": json.dumps(
                {
                    "setting_evidence": world_data.get("setting_evidence", []),
                    "visual_evidence": world_data.get("visual_evidence", []),
                    "style_inference_notes": world_data.get("style_inference_notes", []),
                },
                ensure_ascii=False,
            ),
        }

    elif task == "entity_extraction":
        scene_ref = _scene_ref_from_refs(request.attachment_refs)
        scene_chapters = _chapters_for_scene(project_id, scene_ref) if scene_ref else []
        if not scene_chapters:
            raise HTTPException(status_code=400, detail="识别出图对象必须先关联一个已确认场景正文，请在“当前场景正文”里选择场景。")
        chapter = scene_chapters[0]
        chapter_number = _chapter_number(chapter)
        chapter_title = chapter.get("title", "")
        chapter_text = chapter.get("text", "")[:20000]
        if scene_chapters:
            numbers = [_chapter_number(item) for item in scene_chapters]
            chapter_number = min(numbers)
            chapter_title = f"场景章节：第{min(numbers)}-{max(numbers)}章"
            chapter_text = "\n\n".join([
                f"=== 第{_chapter_number(item)}章 {item.get('title', '')} ===\n{item.get('text', '')}"
                for item in scene_chapters
            ])[:30000]
        extraction_config = load_config().get("extraction", {})
        extractor = EntityExtractor(None, loader, extraction_config)
        extraction_level = request.extraction_level or extraction_config.get("extraction_level", "balanced")
        context = {
            "chapter_number": str(chapter_number),
            "chapter_title": chapter_title,
            "chapter_text": chapter_text,
            "world_bible_summary": _summarize_world_bible(wb),
            "existing_entities": _format_existing_entities(project_id),
            "extraction_level": extraction_level,
            "extraction_level_instruction": extractor._extraction_level_instruction(extraction_level),
        }

    elif task in ("character_attribute", "scene_attribute", "item_attribute"):
        entity = _find_entity(project_id, request.entity_id)
        if task == "character_attribute":
            existing_prompt = _latest_prompt_for_entity(project_id, entity.get("id", ""), "character")
            visual_rules = {
                "face_style": wb.character_visual_rules.face_style,
                "face_style_en": wb.character_visual_rules.face_style_en,
                "clothing_system": wb.character_visual_rules.clothing_system,
                "clothing_materials": wb.character_visual_rules.clothing_materials,
                "hair_style_rules": wb.character_visual_rules.hair_style_rules,
                "accessory_rules": wb.character_visual_rules.accessory_rules,
                "art_style": wb.visual_anchoring.art_style,
                "user_worldview_text": wb.user_worldview_text,
            }
            context = {
                "character_name": entity.get("name", ""),
                "entity_json": json.dumps(entity, ensure_ascii=False, indent=2),
                "existing_attributes": json.dumps(entity.get("attributes", {}), ensure_ascii=False, indent=2),
                "chapter_appearances": _format_chapter_appearances(entity),
                "source_quotes": _format_quotes(entity),
                "existing_prompt": json.dumps(existing_prompt or {}, ensure_ascii=False, indent=2),
                "world_bible_visual_rules": json.dumps(visual_rules, ensure_ascii=False),
            }
        elif task == "scene_attribute":
            context = {
                "scene_name": entity.get("name", ""),
                "source_quotes": _format_quotes(entity),
                "world_bible_scene_rules": json.dumps(
                    {
                        **wb.scene_visual_rules.model_dump(),
                        "user_worldview_text": wb.user_worldview_text,
                    },
                    ensure_ascii=False,
                ),
            }
        else:
            context = {
                "item_name": entity.get("name", ""),
                "source_quotes": _format_quotes(entity),
                "world_bible_item_rules": json.dumps(
                    {
                        **wb.item_visual_rules.model_dump(),
                        "user_worldview_text": wb.user_worldview_text,
                    },
                    ensure_ascii=False,
                ),
            }

    elif task in ("character_prompt", "scene_prompt", "item_prompt"):
        entity = _find_entity(project_id, request.entity_id)
        entity_type = entity.get("type", "character")
        context = {
            "entity_json": json.dumps(entity, ensure_ascii=False, indent=2),
            "world_bible_visual_anchoring": json.dumps(_build_world_context(wb, entity_type), ensure_ascii=False, indent=2),
            "source_quotes": _format_quotes(entity),
        }
        if task == "scene_prompt":
            context["world_bible_scene_rules"] = json.dumps(wb.scene_visual_rules.model_dump(), ensure_ascii=False)
        if task == "item_prompt":
            context["world_bible_item_rules"] = json.dumps(wb.item_visual_rules.model_dump(), ensure_ascii=False)

    elif task == "scene_segmentation":
        chapters = store.load_chapters(project_id)
        if not chapters:
            raise HTTPException(status_code=400, detail="项目还没有章节数据")
        project = store.load_project_info(project_id)
        existing_scenes = _load_scene_groups(project_id)
        start_chapter = request.start_chapter or _next_scene_start_chapter(chapters, existing_scenes)
        granularity = _scene_granularity_config(request.scene_granularity, request.max_chapters)
        last_chapter = _last_chapter_number(chapters)
        if start_chapter > last_chapter:
            raise HTTPException(status_code=400, detail=f"所有章节都已经完成场景分段，下一起点 {start_chapter} 超出最后章节 {last_chapter}")
        chapters_to_analyze = _chapters_from(chapters, start_chapter)
        preview_batch = _slice_chapter_batch(chapters_to_analyze, 0)
        context = {
            "novel_title": project.get("novel_name", project.get("name", "")),
            "start_chapter": start_chapter,
            "last_available_chapter": _chapter_number(chapters_to_analyze[-1]) if chapters_to_analyze else start_chapter,
            "available_chapter_count": len(chapters_to_analyze),
            "has_more_chapters": len(chapters_to_analyze) > len(preview_batch),
            "scene_granularity": request.scene_granularity,
            "granularity_label": granularity["label"],
            "granularity_instruction": granularity["instruction"],
            "existing_scenes": "\n".join([
                f"- {g.get('name', '')}: 第{g.get('chapter_range', '')}章"
                for g in _confirmed_scene_groups(existing_scenes)
            ]) or "（暂无已确认场景）",
            "chapters": _chapter_context(preview_batch),
        }
    else:
        raise HTTPException(status_code=400, detail=f"不支持的 AI 任务: {task}")

    system_prompt, execution_user_prompt = loader.render(task, context)
    display_context = _display_context(task, context)
    _, display_user_prompt = loader.render(task, display_context)
    attachments = _resolve_attachments(project_id, request.attachment_refs)
    previous_run = _find_ai_run(project_id, request.followup_run_id)
    execution_sources = _build_execution_sources(context, attachments)

    display_user_prompt = _append_attachment_refs(display_user_prompt, attachments)
    display_user_prompt = _append_followup_context(display_user_prompt, previous_run)
    display_user_prompt = _append_extra_instruction(display_user_prompt, request.extra_instruction)
    display_user_prompt = _append_visibility_contract(display_user_prompt)

    execution_user_prompt = _append_execution_sources(display_user_prompt, execution_sources)

    return {
        "task": task,
        "context": display_context,
        "execution_context": context,
        "attachments": [
            {
                "ref": attachment.get("ref", ""),
                "label": attachment.get("label", ""),
                "has_content": bool(attachment.get("content")),
            }
            for attachment in attachments
        ],
        "execution_attachments": attachments,
        "execution_sources": execution_sources,
        "followup_run": previous_run,
        "system_prompt": system_prompt,
        "user_prompt": display_user_prompt,
        "execution_user_prompt": execution_user_prompt,
    }


async def _run_scene_segmentation_auto(
    project_id: str,
    request: AiRunRequest,
    prepared: Dict[str, Any],
    system_prompt: str,
    display_user_prompt: str,
) -> Dict[str, Any]:
    loader = _get_prompt_loader()
    llm = _get_llm()
    chapters = store.load_chapters(project_id)
    existing_scenes = _load_scene_groups(project_id)
    start_chapter = request.start_chapter or prepared.get("execution_context", {}).get("start_chapter") or _next_scene_start_chapter(chapters, existing_scenes)
    all_remaining = _chapters_from(chapters, int(start_chapter))
    if not all_remaining:
        raise HTTPException(status_code=400, detail="没有更多章节需要分析")

    base_context = dict(prepared.get("execution_context", prepared.get("context", {})))
    accumulated: List[dict] = []
    raw_outputs: List[str] = []
    execution_prompts: List[str] = []
    last_result: Optional[Dict[str, Any]] = None

    for round_index in range(SCENE_SEGMENT_MAX_INTERNAL_ROUNDS):
        offset = round_index * SCENE_SEGMENT_BATCH_CHAPTERS
        batch = _slice_chapter_batch(all_remaining, offset)
        if not batch:
            break

        accumulated.extend(batch)
        has_more = offset + len(batch) < len(all_remaining)
        context = {
            **base_context,
            "chapters": _chapter_context(accumulated),
            "last_available_chapter": _chapter_number(accumulated[-1]),
            "available_chapter_count": len(all_remaining),
            "has_more_chapters": has_more,
        }
        _, template_user_prompt = loader.render("scene_segmentation", context)
        if request.user_prompt is not None:
            chapter_sources = _build_execution_sources({"chapters": context["chapters"]}, [])
            user_prompt = _append_execution_sources(
                f"{display_user_prompt}\n\n【系统自动续读状态】\n本轮已连续读取到第 {context['last_available_chapter']} 章；如果仍未看到边界，系统会继续读取后续章节。",
                chapter_sources,
            )
        else:
            user_prompt = template_user_prompt
            user_prompt = _append_followup_context(user_prompt, prepared.get("followup_run"))
            user_prompt = _append_extra_instruction(user_prompt, request.extra_instruction)
            user_prompt = _append_visibility_contract(user_prompt)

        result = await llm.generate_json_with_raw_async(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )
        parsed = result["parsed_output"]
        raw_outputs.append(result["raw_output"])
        execution_prompts.append(result["user_prompt"])
        last_result = result

        scene_data = parsed.get("scene", {}) if isinstance(parsed, dict) else {}
        analysis = parsed.get("analysis", {}) if isinstance(parsed, dict) else {}
        needs_more = bool(analysis.get("needs_more_chapters"))
        if scene_data and (not needs_more or not has_more):
            break

    if not last_result:
        raise HTTPException(status_code=502, detail="AI 未返回场景分段结果")

    parsed_output = last_result["parsed_output"]
    parsed_output.setdefault("analysis", {})
    parsed_output["analysis"]["internal_read_rounds"] = len(raw_outputs)
    parsed_output["analysis"]["internal_read_chapters"] = [
        _chapter_number(chapter)
        for chapter in accumulated
    ]

    return {
        "raw_output": "\n\n--- 内部续读轮次 ---\n\n".join(raw_outputs),
        "parsed_output": parsed_output,
        "system_prompt": system_prompt,
        "user_prompt": "\n\n--- 内部续读轮次 ---\n\n".join(execution_prompts),
        "display_user_prompt": display_user_prompt,
    }


def _apply_result(project_id: str, request: AiRunRequest, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if request.task == "world_bible_analyze":
        current = store.load_world_bible(project_id) if (store.get_project_dir(project_id) / "data" / "world_bible.json").exists() else {}
        current["world_framework"] = {
            key: parsed.get(key, "")
            for key in [
                "genre",
                "sub_genre",
                "era_setting",
                "technology_level",
                "power_system",
                "social_structure",
                "geography_overview",
                "tone_and_mood",
            ]
        }
        current["world_framework"]["key_concepts"] = parsed.get("key_concepts", [])
        current["setting_evidence"] = parsed.get("setting_evidence", [])
        current["visual_evidence"] = parsed.get("visual_evidence", [])
        current["style_inference_notes"] = parsed.get("style_inference_notes", [])
        current.setdefault("project_id", project_id)
        store.save_world_bible(project_id, current)
        return {"target": "world_bible", "message": "已更新世界观框架"}

    if request.task == "visual_anchoring":
        current = store.load_world_bible(project_id)
        for key in ["visual_anchoring", "character_visual_rules", "scene_visual_rules", "item_visual_rules"]:
            if key in parsed:
                current[key] = parsed[key]
        if "consistency_notes" in parsed:
            current["consistency_notes"] = parsed["consistency_notes"]
        store.save_world_bible(project_id, current)
        return {"target": "world_bible", "message": "已更新视觉锚定"}

    if request.task in ("character_attribute", "scene_attribute", "item_attribute"):
        entity = _find_entity(project_id, request.entity_id)
        entities = store.load_entities(project_id)
        for idx, current in enumerate(entities):
            if current.get("id") == entity.get("id"):
                if request.task == "character_attribute":
                    merge_stats = _merge_character_attribute_result(current, parsed, request)
                    entities[idx] = current
                    store.save_entities(project_id, entities)
                    return {
                        "target": "entity",
                        "message": (
                            "已合并角色视觉设定"
                            f"：新增 {merge_stats['added_source_quotes']} 条引用、"
                            f"{merge_stats['added_chapter_appearances']} 条章节/阶段记录。"
                            "如需用于生图，请重新生成该角色绘图指令。"
                        ),
                        "entity_id": current.get("id"),
                        **merge_stats,
                    }
                current["attributes"] = parsed.get("attributes", parsed)
                entities[idx] = current
                store.save_entities(project_id, entities)
                return {"target": "entity", "message": "已更新实体属性", "entity_id": current.get("id")}

    if request.task == "entity_extraction":
        candidates = _parse_entity_candidates(parsed, _fallback_chapter_for_request(project_id, request))
        existing = [Entity(**entity) for entity in store.load_entities(project_id)]
        merged = EntityMerger().merge(candidates, existing, project_id=project_id)
        store.save_entities(project_id, [entity.model_dump() for entity in merged])
        return {
            "target": "entities",
            "message": f"已合并写入 {len(candidates)} 个候选实体，当前实体总数 {len(merged)}",
            "candidate_count": len(candidates),
            "entity_count": len(merged),
        }

    if request.task in ("character_prompt", "scene_prompt", "item_prompt"):
        entity = _find_entity(project_id, request.entity_id)
        prompt = _to_prompt(parsed, entity, request.task)
        prompts = store.load_prompts(project_id)
        prompts = [
            item for item in prompts
            if not (item.get("entity_id") == prompt["entity_id"] and item.get("type") == prompt["type"])
        ]
        prompts.insert(0, prompt)
        store.save_prompts(project_id, prompts)
        store.save_prompts_md(project_id, prompts, "prompts.md")
        return {
            "target": "prompts",
            "message": f"已写入 {prompt['type']} 提示词",
            "prompt_id": prompt["id"],
            "entity_id": prompt["entity_id"],
        }

    if request.task == "scene_segmentation":
        scene_data = parsed.get("scene", {})
        if not scene_data:
            return {"target": "scene_groups", "message": "未发现可写入的场景分段"}
        existing_groups = _load_scene_groups(project_id)
        chapters = store.load_chapters(project_id)
        fallback_start = request.start_chapter or _next_scene_start_chapter(chapters, existing_groups)
        analyzed_max = max(
            [_chapter_number(chapter, index + 1) for index, chapter in enumerate(chapters) if _chapter_number(chapter, index + 1) >= fallback_start],
            default=fallback_start,
        )
        start_ch = int(scene_data.get("start_chapter", fallback_start) or fallback_start)
        end_ch = int(scene_data.get("end_chapter", start_ch) or start_ch)

        if start_ch != fallback_start:
            start_ch = fallback_start
        if end_ch < start_ch:
            end_ch = start_ch
        if end_ch > analyzed_max:
            end_ch = analyzed_max

        group = {
            "id": f"scene_{start_ch}_{end_ch}_{str(uuid.uuid4())[:4]}",
            "name": scene_data.get("name", f"场景 {start_ch}-{end_ch}"),
            "chapter_range": f"{start_ch}-{end_ch}",
            "chapters": list(range(start_ch, end_ch + 1)),
            "description": scene_data.get("description", ""),
            "confidence": scene_data.get("confidence", 0.8),
            "granularity": request.scene_granularity,
            "reasoning": parsed.get("analysis", {}).get("readable_report", "") or parsed.get("readable_report", "") or json.dumps(parsed.get("analysis", {}), ensure_ascii=False),
            "transition_after": scene_data.get("transition_after", ""),
            "visual_focus": scene_data.get("visual_focus", []),
            "source": "ai",
        }
        existing_groups.append(group)
        _save_scene_groups(project_id, existing_groups)
        return {
            "target": "scene_groups",
            "message": f"已写入场景分组：{group['name']}",
            "group_id": group["id"],
            "next_start_chapter": end_ch + 1,
        }

    return None


def _parse_entity_candidates(parsed: Dict[str, Any], fallback_chapter: int) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    def add_common(item: Dict[str, Any], entity_type: str) -> None:
        chapter = int(item.get("chapter") or fallback_chapter or 0)
        candidates.append({
            "name": item.get("name", ""),
            "aliases": item.get("aliases", []),
            "type": entity_type,
            "brief_description": item.get("brief_description", ""),
            "source_quote": item.get("source_quote", ""),
            "confidence": item.get("confidence", 0.8),
            "is_new": item.get("is_new", True),
            "chapter": chapter,
            "location": item.get("location", f"第{chapter}章"),
            "context": item.get("context", ""),
            "appearance_note": item.get("appearance_note", ""),
            "clothing_override": item.get("clothing_override", ""),
            "category": item.get("category", ""),
        })

    for item in parsed.get("characters", []):
        add_common(item, "character")
    for item in parsed.get("scenes", []):
        add_common(item, "scene")
    for item in parsed.get("items", []):
        add_common(item, "item")

    return [candidate for candidate in candidates if candidate.get("name")]


def _to_prompt(parsed: Dict[str, Any], entity: Dict[str, Any], task: str) -> Dict[str, Any]:
    prompt_type = task.replace("_prompt", "")
    params = parsed.get("parameters", {}) or {}
    default_ar = {"character": "3:4", "scene": "16:9", "item": "1:1"}.get(prompt_type, "1:1")
    prompt = Prompt(
        id=str(uuid.uuid4())[:8],
        entity_id=entity.get("id", ""),
        type=prompt_type,
        world_prefix_chinese=parsed.get("world_prefix_chinese", ""),
        face_block_chinese=parsed.get("face_block_chinese", ""),
        chinese_prompt=parsed.get("chinese_prompt", ""),
        negative_prompt=parsed.get("negative_prompt", ""),
        style_tags=parsed.get("style_tags", []),
        parameters=PromptParameters(
            aspect_ratio=params.get("aspect_ratio", default_ar),
            steps=params.get("steps", 30),
            cfg_scale=params.get("cfg_scale", 7.0),
            sampler=params.get("sampler", "DPM++ 2M Karras"),
        ),
        source_quotes=entity.get("source_quotes", []),
    )
    return prompt.model_dump()


@router.get("/{project_id}/ai/tasks")
async def list_ai_tasks(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return {"tasks": TASKS}


@router.get("/{project_id}/ai/attachments")
async def list_ai_attachments(project_id: str):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return {"attachments": _get_attachment_catalog(project_id)}


@router.post("/{project_id}/ai/attachment-content")
async def get_ai_attachment_content(project_id: str, request: AiAttachmentContentRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    attachments = _resolve_attachments(project_id, [request.ref])
    if not attachments:
        raise HTTPException(status_code=404, detail=f"关联内容不存在: {request.ref}")

    attachment = attachments[0]
    content = attachment.get("content", "")
    return {
        "ref": attachment.get("ref", request.ref),
        "label": attachment.get("label", request.ref),
        "content": content,
        "chars": len(content),
    }


@router.get("/{project_id}/ai/runs")
async def list_ai_runs(project_id: str, limit: int = 30):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return {"runs": [_public_run(run) for run in store.load_ai_runs(project_id)[:limit]]}


@router.post("/{project_id}/ai/prepare")
async def prepare_ai_run(project_id: str, request: AiPrepareRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")
    return _public_prepared(_prepare_prompt(project_id, request))


@router.post("/{project_id}/ai/run")
async def run_ai_task(project_id: str, request: AiRunRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    prepared = _prepare_prompt(project_id, request)
    system_prompt = request.system_prompt if request.system_prompt is not None else prepared["system_prompt"]
    display_user_prompt = request.user_prompt if request.user_prompt is not None else prepared["user_prompt"]
    execution_user_prompt = _append_execution_sources(
        display_user_prompt,
        prepared.get("execution_sources", []),
    )
    try:
        if request.task == "scene_segmentation":
            result = await _run_scene_segmentation_auto(
                project_id,
                request,
                prepared,
                system_prompt,
                display_user_prompt,
            )
        else:
            result = await _get_llm().generate_json_with_raw_async(
                prompt=execution_user_prompt,
                system_prompt=system_prompt,
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 接口调用失败: {str(e)}")

    applied = _apply_result(project_id, request, result["parsed_output"]) if request.apply_result else None

    run = {
        "id": str(uuid.uuid4())[:8],
        "task": request.task,
        "chapter_number": request.chapter_number,
        "entity_id": request.entity_id,
        "extra_instruction": request.extra_instruction,
        "followup_run_id": request.followup_run_id,
        "context": prepared["context"],
        "execution_context": prepared.get("execution_context", prepared["context"]),
        "attachments": prepared.get("attachments", []),
        "execution_attachments": prepared.get("execution_attachments", []),
        "followup_run": prepared.get("followup_run"),
        "system_prompt": system_prompt,
        "user_prompt": display_user_prompt,
        "execution_user_prompt": result["user_prompt"],
        "template_system_prompt": prepared["system_prompt"],
        "template_user_prompt": prepared["user_prompt"],
        "template_execution_user_prompt": prepared.get("execution_user_prompt", prepared["user_prompt"]),
        "raw_output": result["raw_output"],
        "parsed_output": result["parsed_output"],
        "applied": applied,
        "created_at": datetime.now().isoformat(),
    }
    store.append_ai_run(project_id, run)
    return {"run": _public_run(run)}


@router.post("/{project_id}/ai/apply")
async def apply_ai_run(project_id: str, request: AiApplyRequest):
    if not store.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

    runs = store.load_ai_runs(project_id)
    target_run = None
    for run in runs:
        if run.get("id") == request.run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail=f"AI 记录不存在: {request.run_id}")

    apply_request = AiRunRequest(
        task=target_run.get("task", ""),
        chapter_number=target_run.get("chapter_number"),
        entity_id=target_run.get("entity_id"),
        start_chapter=target_run.get("context", {}).get("start_chapter"),
        max_chapters=target_run.get("context", {}).get("max_chapters"),
        scene_granularity=target_run.get("context", {}).get("scene_granularity", target_run.get("context", {}).get("granularity", "medium")),
        extra_instruction=target_run.get("extra_instruction", ""),
        attachment_refs=[attachment.get("ref", "") for attachment in target_run.get("attachments", [])],
        apply_result=True,
    )
    applied = _apply_result(project_id, apply_request, target_run.get("parsed_output", {}))
    target_run["applied"] = applied
    target_run["applied_at"] = datetime.now().isoformat()
    store.save_ai_runs(project_id, runs)
    return {"run": _public_run(target_run)}
