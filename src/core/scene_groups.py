from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


SCENE_SEGMENT_BATCH_CHAPTERS = 12
SCENE_SEGMENT_MAX_INTERNAL_ROUNDS = 20

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


class ProjectStoreLike(Protocol):
    def get_project_dir(self, project_id: str) -> Path:
        ...


_default_store: ProjectStoreLike | None = None


def _project_store(project_store: ProjectStoreLike | None = None) -> ProjectStoreLike:
    global _default_store
    if project_store is not None:
        return project_store
    if _default_store is None:
        from src.storage.project_store import ProjectStore

        _default_store = ProjectStore()
    return _default_store


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _positive_ints(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []

    numbers: list[int] = []
    for value in values:
        number = _safe_int(value)
        if number > 0:
            numbers.append(number)
    return numbers


def scene_granularity_config(granularity: str, max_chapters: int | None = None) -> dict[str, str]:
    config = dict(SCENE_GRANULARITY.get(granularity, SCENE_GRANULARITY["medium"]))
    if max_chapters and max_chapters > 0:
        config["instruction"] = (
            f"{config['instruction']} 用户本次设置了单个场景最多约 {max_chapters} 章；"
            "优先按自然剧情边界判断，接近上限仍未出现明确边界时应保守截断并说明不确定性。"
        )
    return config


def parse_chapter_range(range_str: str) -> list[int]:
    chapters: list[int] = []
    if not range_str:
        return chapters

    for part in str(range_str).split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = [int(value.strip()) for value in part.split("-", 1)]
                if start > end:
                    start, end = end, start
                chapters.extend(range(start, end + 1))
            except Exception:
                continue
        else:
            try:
                chapters.append(int(part))
            except Exception:
                continue

    return sorted(set(chapters))


def get_chapter_number(chapter: dict[str, Any], fallback: int = 0) -> int:
    for key in ("number", "chapter_number", "index"):
        if key not in chapter:
            continue
        value = _safe_int(chapter.get(key))
        if value:
            return value
    return fallback


def chapters_from(chapters: list[dict[str, Any]], start_chapter: int) -> list[dict[str, Any]]:
    return [
        chapter for chapter in chapters
        if get_chapter_number(chapter) >= start_chapter
    ]


def select_chapters_from_number(chapters: list[dict[str, Any]], start_chapter: int) -> list[dict[str, Any]]:
    return chapters_from(chapters, start_chapter)


def chapter_context(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "number": get_chapter_number(chapter, index + 1),
            "title": chapter.get("title", f"第{index + 1}章"),
            "text": chapter.get("text", ""),
        }
        for index, chapter in enumerate(chapters)
    ]


def slice_chapter_batch(
    chapters: list[dict[str, Any]],
    offset: int,
    batch_size: int = SCENE_SEGMENT_BATCH_CHAPTERS,
) -> list[dict[str, Any]]:
    return chapters[offset:offset + batch_size]


def group_end_chapter(group: dict[str, Any]) -> int:
    chapters = _positive_ints(group.get("chapters"))
    if chapters:
        return max(chapters)

    parsed = parse_chapter_range(group.get("chapter_range", ""))
    return max(parsed) if parsed else 0


def group_start_chapter(group: dict[str, Any]) -> int:
    chapters = _positive_ints(group.get("chapters"))
    if chapters:
        return min(chapters)

    parsed = parse_chapter_range(group.get("chapter_range", ""))
    return min(parsed) if parsed else 0


def scene_chapters(scene: dict[str, Any]) -> set[int]:
    chapters = set(_positive_ints(scene.get("chapters")))
    if not chapters:
        chapters.update(parse_chapter_range(scene.get("chapter_range", "")))
    return chapters


def confirmed_scene_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        group for group in groups
        if not group.get("source") or group.get("source") in {"ai", "manual"}
    ]


def last_chapter_number(chapters: list[dict[str, Any]]) -> int:
    chapter_numbers = [
        get_chapter_number(chapter, index + 1)
        for index, chapter in enumerate(chapters)
    ]
    return max(chapter_numbers) if chapter_numbers else 0


def next_scene_start_chapter(chapters: list[dict[str, Any]], groups: list[dict[str, Any]]) -> int:
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


def scene_groups_path(project_id: str, project_store: ProjectStoreLike | None = None) -> Path:
    return _project_store(project_store).get_project_dir(project_id) / "scene_groups.json"


def load_scene_groups(
    project_id: str,
    project_store: ProjectStoreLike | None = None,
) -> list[dict[str, Any]]:
    groups_file = scene_groups_path(project_id, project_store)
    if not groups_file.exists():
        return []
    try:
        with open(groups_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_scene_groups(
    project_id: str,
    groups: list[dict[str, Any]],
    project_store: ProjectStoreLike | None = None,
) -> None:
    groups_file = scene_groups_path(project_id, project_store)
    with open(groups_file, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)
