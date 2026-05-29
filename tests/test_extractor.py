import pytest
import sys
from pathlib import Path
import tempfile
import os
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.entity import Entity, EntityType, SourceQuote, WorldBinding
from src.core.entity_merger import EntityMerger


class TestEntityMerger:
    """实体合并器测试"""

    def setup_method(self):
        """设置测试环境"""
        self.config = {
            "dedup_similarity_threshold": 0.85,
            "min_alias_similarity": 0.8,
        }
        self.merger = EntityMerger(self.config)

    def test_merge_new_entity(self):
        """测试合并新实体"""
        candidates = [
            {
                "name": "张三",
                "aliases": ["张三丰"],
                "type": "character",
                "brief_description": "主角",
                "source_quote": "张三是个勇敢的人",
                "confidence": 0.9,
                "chapter": 1,
            }
        ]
        existing = []
        result = self.merger.merge(candidates, existing, "test_project")

        assert len(result) == 1
        assert result[0].name == "张三"
        assert "张三丰" in result[0].aliases

    def test_merge_same_entity(self):
        """测试合并相同实体"""
        existing_entity = Entity(
            id="char_001",
            project_id="test_project",
            name="张三",
            aliases=["张三丰"],
            type=EntityType.CHARACTER,
            source_quotes=[
                SourceQuote(
                    chapter=1,
                    text="张三是个勇敢的人",
                    location="第1章"
                )
            ],
            first_appearance_chapter=1,
        )

        candidates = [
            {
                "name": "张三",
                "aliases": ["张三侠"],
                "type": "character",
                "brief_description": "主角",
                "source_quote": "张三在战斗中展现了勇气",
                "confidence": 0.9,
                "chapter": 2,
            }
        ]

        result = self.merger.merge(candidates, [existing_entity], "test_project")

        assert len(result) == 1
        assert "张三侠" in result[0].aliases
        assert len(result[0].source_quotes) == 2

    def test_merge_similar_name(self):
        """测试合并相似名称 - 使用完全相同的名称"""
        existing_entity = Entity(
            id="char_001",
            project_id="test_project",
            name="张三",
            type=EntityType.CHARACTER,
        )

        candidates = [
            {
                "name": "张三",
                "aliases": [],
                "type": "character",
                "brief_description": "主角",
                "confidence": 0.9,
                "chapter": 1,
            }
        ]

        result = self.merger.merge(candidates, [existing_entity], "test_project")

        assert len(result) == 1

    def test_merge_different_types(self):
        """测试不同类型不合并"""
        existing_entity = Entity(
            id="char_001",
            project_id="test_project",
            name="张三",
            type=EntityType.CHARACTER,
        )

        candidates = [
            {
                "name": "张三",
                "aliases": [],
                "type": "scene",
                "brief_description": "场景名",
                "confidence": 0.9,
                "chapter": 1,
            }
        ]

        result = self.merger.merge(candidates, [existing_entity], "test_project")

        assert len(result) == 2

    def test_merge_scene_entity(self):
        """测试合并场景实体"""
        candidates = [
            {
                "name": "神秘森林",
                "aliases": [],
                "type": "scene",
                "brief_description": "位于王国北部的古老森林",
                "source_quote": "他们进入了神秘森林",
                "confidence": 0.85,
                "chapter": 1,
            }
        ]

        result = self.merger.merge(candidates, [], "test_project")

        assert len(result) == 1
        assert result[0].name == "神秘森林"
        assert result[0].type == EntityType.SCENE

    def test_merge_item_entity(self):
        """测试合并物品实体"""
        candidates = [
            {
                "name": "神剑",
                "aliases": ["倚天剑"],
                "type": "item",
                "brief_description": "一把传说中的神兵利器",
                "confidence": 0.9,
                "chapter": 1,
            }
        ]

        result = self.merger.merge(candidates, [], "test_project")

        assert len(result) == 1
        assert result[0].name == "神剑"
        assert result[0].type == EntityType.ITEM

    def test_find_duplicates(self):
        """测试查找重复实体"""
        entities = [
            Entity(id="char_001", project_id="test", name="张三", type=EntityType.CHARACTER),
            Entity(id="char_002", project_id="test", name="张 三", type=EntityType.CHARACTER),
            Entity(id="char_003", project_id="test", name="李四", type=EntityType.CHARACTER),
        ]

        duplicates = self.merger.find_duplicates(entities)

        assert len(duplicates) >= 1

    def test_similarity_calculation(self):
        """测试相似度计算"""
        sim1 = self.merger._similarity("张三", "张三")
        assert sim1 == 1.0

        sim2 = self.merger._similarity("张三", "李四")
        assert sim2 < 1.0

        sim3 = self.merger._similarity("张三", "张三四")
        assert sim3 > 0.5


class TestEntity:
    """实体模型测试"""

    def test_create_character_entity(self):
        """测试创建角色实体"""
        entity = Entity(
            id="char_001",
            project_id="proj_001",
            name="张三",
            type=EntityType.CHARACTER,
            aliases=["张三丰"],
            source_quotes=[
                SourceQuote(chapter=1, text="张三是个勇敢的人", location="第1章")
            ],
            first_appearance_chapter=1,
        )

        assert entity.name == "张三"
        assert entity.type == EntityType.CHARACTER
        assert "张三丰" in entity.aliases
        assert len(entity.source_quotes) == 1

    def test_create_scene_entity(self):
        """测试创建场景实体"""
        entity = Entity(
            id="scene_001",
            project_id="proj_001",
            name="神秘森林",
            type=EntityType.SCENE,
            source_quotes=[
                SourceQuote(chapter=1, text="森林中充满了神秘", location="第1章")
            ],
        )

        assert entity.type == EntityType.SCENE
        assert entity.name == "神秘森林"

    def test_entity_defaults(self):
        """测试实体默认值"""
        entity = Entity()
        assert entity.name == ""
        assert entity.type == EntityType.CHARACTER
        assert entity.aliases == []
        assert entity.source_quotes == []

    def test_entity_type_enum(self):
        """测试实体类型枚举"""
        assert EntityType.CHARACTER.value == "character"
        assert EntityType.SCENE.value == "scene"
        assert EntityType.ITEM.value == "item"
        assert EntityType.CREATURE.value == "creature"

    def test_world_binding(self):
        """测试世界观绑定"""
        binding = WorldBinding(
            genre="仙侠",
            era="古代",
            face_style="古典面容",
            clothing_system="古装",
            art_style="古风水墨",
        )

        assert binding.genre == "仙侠"
        assert binding.era == "古代"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
