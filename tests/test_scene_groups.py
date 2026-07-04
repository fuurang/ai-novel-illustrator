from pathlib import Path

from src.core.scene_groups import (
    chapter_context,
    confirmed_scene_groups,
    get_chapter_number,
    group_end_chapter,
    group_start_chapter,
    load_scene_groups,
    next_scene_start_chapter,
    parse_chapter_range,
    save_scene_groups,
    scene_chapters,
    scene_granularity_config,
)


class DummyStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def get_project_dir(self, project_id: str) -> Path:
        path = self.base_dir / project_id
        path.mkdir(parents=True, exist_ok=True)
        return path


def test_parse_chapter_range_dedupes_and_normalizes_reversed_ranges():
    assert parse_chapter_range("3, 1-2, 5-4, bad, 2") == [1, 2, 3, 4, 5]


def test_get_chapter_number_falls_back_for_invalid_values():
    assert get_chapter_number({"number": "bad", "chapter_number": 9}, fallback=7) == 9
    assert get_chapter_number({"chapter_number": "8"}, fallback=1) == 8
    assert get_chapter_number({"index": 0}, fallback=6) == 6


def test_chapter_context_adds_stable_defaults():
    context = chapter_context([
        {"number": "2", "title": "Named", "text": "A"},
        {"chapter_number": "bad", "text": "B"},
    ])

    assert context == [
        {"number": 2, "title": "Named", "text": "A"},
        {"number": 2, "title": "第2章", "text": "B"},
    ]


def test_group_boundaries_ignore_bad_chapter_values_before_range_fallback():
    group = {"chapters": ["4", "bad", 2, 0], "chapter_range": "10-12"}
    assert group_start_chapter(group) == 2
    assert group_end_chapter(group) == 4

    fallback_group = {"chapters": ["bad"], "chapter_range": "12-10"}
    assert group_start_chapter(fallback_group) == 10
    assert group_end_chapter(fallback_group) == 12


def test_scene_chapters_uses_range_when_chapter_list_has_no_valid_numbers():
    assert scene_chapters({"chapters": ["x", 0], "chapter_range": "6-7"}) == {6, 7}


def test_next_scene_start_uses_only_confirmed_contiguous_groups():
    chapters = [{"number": number} for number in range(1, 8)]
    groups = [
        {"source": "quick", "chapters": [1, 2, 3]},
        {"source": "ai", "chapters": [1, 2]},
        {"source": "manual", "chapter_range": "3-4"},
        {"source": "ai", "chapter_range": "6-7"},
    ]

    assert confirmed_scene_groups(groups) == groups[1:]
    assert next_scene_start_chapter(chapters, groups) == 5


def test_scene_granularity_includes_optional_max_chapter_instruction():
    config = scene_granularity_config("unknown", max_chapters=6)

    assert config["label"] == "中"
    assert "最多约 6 章" in config["instruction"]


def test_load_and_save_scene_groups_round_trip(tmp_path):
    store = DummyStore(tmp_path)
    groups = [{"id": "scene_1", "chapters": [1], "source": "manual"}]

    save_scene_groups("project_1", groups, store)

    assert load_scene_groups("project_1", store) == groups
    assert load_scene_groups("missing_project", store) == []
