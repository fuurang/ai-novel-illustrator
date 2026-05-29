import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.prompt import Prompt, PromptParameters
from src.models.entity import Entity, EntityType
from src.models.world_bible import WorldBible, WorldFramework, VisualAnchoring, ColorPalette


class TestPromptParameters:
    """提示词参数测试"""

    def test_create_parameters(self):
        """测试创建参数"""
        params = PromptParameters(
            aspect_ratio="3:4",
            steps=30,
            cfg_scale=7.0,
            sampler="DPM++ 2M Karras"
        )

        assert params.aspect_ratio == "3:4"
        assert params.steps == 30
        assert params.cfg_scale == 7.0
        assert params.sampler == "DPM++ 2M Karras"

    def test_parameters_defaults(self):
        """测试参数默认值"""
        params = PromptParameters()

        assert params.aspect_ratio == "1:1"
        assert params.steps == 30
        assert params.cfg_scale == 7.0
        assert params.sampler == "DPM++ 2M Karras"


class TestPrompt:
    """提示词模型测试"""

    def test_create_character_prompt(self):
        """测试创建角色提示词"""
        prompt = Prompt(
            id="prompt_001",
            entity_id="char_001",
            type="character",
            world_prefix_chinese="[古风水墨] 仙侠 神秘",
            world_prefix_english="Ancient Chinese ink painting style, Xianxia, mystical",
            face_block_chinese="俊美面容，长发束冠，眼神深邃",
            face_block_english="Handsome face, long hair tied up, deep eyes",
            chinese_prompt="[古风水墨] 仙侠 神秘 角色 张三，俊美面容，长发束冠，身穿白色道袍",
            english_prompt="Ancient Chinese ink painting style, Xianxia, mystical, character Zhang San, handsome face, white Taoist robe",
            negative_prompt="现代建筑, 低质量, 模糊, 变形",
            style_tags=["古风", "仙侠", "水墨"],
            parameters=PromptParameters(aspect_ratio="3:4"),
            source_quotes=[
                {"chapter": 1, "text": "张三身穿白色道袍", "location": "第1章"}
            ]
        )

        assert prompt.id == "prompt_001"
        assert prompt.entity_id == "char_001"
        assert prompt.type == "character"
        assert "古风" in prompt.style_tags
        assert prompt.parameters.aspect_ratio == "3:4"

    def test_create_scene_prompt(self):
        """测试创建场景提示词"""
        prompt = Prompt(
            id="prompt_002",
            entity_id="scene_001",
            type="scene",
            world_prefix_chinese="[古风水墨] 仙侠",
            world_prefix_english="Ancient Chinese ink painting style, Xianxia",
            chinese_prompt="[古风水墨] 仙侠 神秘森林，古老的树木参天，雾气缭绕",
            english_prompt="Ancient Chinese ink painting style, Xianxia, mysterious forest, ancient towering trees, mist swirling",
            negative_prompt="现代建筑, 人类, 低质量",
            parameters=PromptParameters(aspect_ratio="16:9"),
        )

        assert prompt.type == "scene"
        assert prompt.parameters.aspect_ratio == "16:9"

    def test_create_item_prompt(self):
        """测试创建物品提示词"""
        prompt = Prompt(
            id="prompt_003",
            entity_id="item_001",
            type="item",
            chinese_prompt="[古风] 神剑，金色剑身，剑柄镶有宝石",
            english_prompt="Ancient style, divine sword, golden blade, gem-inlaid hilt",
            parameters=PromptParameters(aspect_ratio="1:1"),
        )

        assert prompt.type == "item"
        assert prompt.parameters.aspect_ratio == "1:1"

    def test_prompt_serialization(self):
        """测试提示词序列化"""
        prompt = Prompt(
            id="prompt_test",
            entity_id="char_test",
            type="character",
            chinese_prompt="测试提示词",
            english_prompt="test prompt",
            parameters=PromptParameters(),
        )

        data = prompt.model_dump()

        assert data['id'] == "prompt_test"
        assert data['entity_id'] == "char_test"
        assert data['type'] == "character"
        assert data['chinese_prompt'] == "测试提示词"
        assert data['english_prompt'] == "test prompt"

    def test_prompt_deserialization(self):
        """测试提示词反序列化"""
        data = {
            'id': 'prompt_test',
            'entity_id': 'char_test',
            'type': 'character',
            'world_prefix_chinese': '',
            'world_prefix_english': '',
            'face_block_chinese': '',
            'face_block_english': '',
            'chinese_prompt': '测试中文提示词',
            'english_prompt': 'test english prompt',
            'negative_prompt': '',
            'style_tags': ['test'],
            'parameters': {
                'aspect_ratio': '3:4',
                'steps': 25,
                'cfg_scale': 6.5,
                'sampler': 'Euler',
            },
            'source_quotes': [],
        }

        prompt = Prompt(**data)

        assert prompt.id == 'prompt_test'
        assert prompt.parameters.aspect_ratio == '3:4'
        assert prompt.parameters.steps == 25


class TestPromptGeneratorLogic:
    """提示词生成逻辑测试（不依赖 LLM）"""

    def test_world_bible_for_prompt(self):
        """测试世界观信息用于提示词生成"""
        wb = WorldBible(
            id="wb_001",
            project_id="proj_001",
            novel_title="仙侠小说",
            world_framework=WorldFramework(
                genre="仙侠",
                sub_genre="玄幻",
                era_setting="古代",
                power_system="修真体系",
            ),
            visual_anchoring=VisualAnchoring(
                art_style="古风水墨",
                art_style_en="Ancient Chinese ink painting style",
                color_palette=ColorPalette(
                    primary="蓝色",
                    secondary="白色",
                    accent="金色",
                    mood="神秘",
                    specific_colors=["#87CEEB", "#F5F5DC", "#DAA520"],
                ),
                lighting_style="自然光",
                texture_style="细腻质感",
                atmosphere_keywords=["仙侠", "古风", "神秘"],
                atmosphere_keywords_en=["Xianxia", "Ancient", "Mystical"],
                forbidden_elements=["现代建筑", "高科技"],
            ),
        )

        assert wb.world_framework.genre == "仙侠"
        assert wb.visual_anchoring.art_style == "古风水墨"
        assert "仙侠" in wb.visual_anchoring.atmosphere_keywords
        assert "现代建筑" in wb.visual_anchoring.forbidden_elements

    def test_entity_attributes_for_prompt(self):
        """测试实体属性用于提示词生成"""
        entity = Entity(
            id="char_001",
            project_id="proj_001",
            name="张三",
            type=EntityType.CHARACTER,
            attributes={
                "gender": "男",
                "age_range": "二十岁左右",
                "appearance": {
                    "face": "俊美面容，剑眉星目",
                    "hair": "黑色长发，用玉簪束起",
                    "body": "身材修长，气质出尘",
                    "distinguishing_features": "左手背有神秘印记",
                },
                "clothing": {
                    "default": "白色道袍，腰系玉带",
                    "variations": [],
                },
            },
        )

        attrs = entity.attributes
        assert attrs["gender"] == "男"
        assert "俊美面容" in attrs["appearance"]["face"]
        assert "白色道袍" in attrs["clothing"]["default"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
