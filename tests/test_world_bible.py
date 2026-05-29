import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.world_bible import (
    WorldBible,
    WorldFramework,
    VisualAnchoring,
    ColorPalette,
    CharacterVisualRules,
    SceneVisualRules,
    ItemVisualRules,
)


class TestWorldFramework:
    """世界观框架测试"""

    def test_create_framework(self):
        """测试创建世界观框架"""
        framework = WorldFramework(
            genre="仙侠",
            sub_genre="玄幻",
            era_setting="古代",
            technology_level="修真文明",
            power_system="修真体系",
            social_structure="门派宗门制度",
            geography_overview="九州大陆",
            key_concepts=["修仙", "飞升", "渡劫"],
            tone_and_mood="神秘、飘逸、超然",
        )

        assert framework.genre == "仙侠"
        assert framework.sub_genre == "玄幻"
        assert framework.era_setting == "古代"
        assert framework.power_system == "修真体系"
        assert len(framework.key_concepts) == 3

    def test_framework_defaults(self):
        """测试世界观框架默认值"""
        framework = WorldFramework()

        assert framework.genre == ""
        assert framework.sub_genre == ""
        assert framework.era_setting == ""
        assert framework.key_concepts == []


class TestColorPalette:
    """色彩调色板测试"""

    def test_create_palette(self):
        """测试创建调色板"""
        palette = ColorPalette(
            primary="蓝色",
            secondary="白色",
            accent="金色",
            mood="神秘",
            specific_colors=["#87CEEB", "#F5F5DC", "#DAA520", "#2F4F4F"],
        )

        assert palette.primary == "蓝色"
        assert palette.secondary == "白色"
        assert palette.accent == "金色"
        assert palette.mood == "神秘"
        assert len(palette.specific_colors) == 4

    def test_palette_defaults(self):
        """测试调色板默认值"""
        palette = ColorPalette()

        assert palette.primary == ""
        assert palette.secondary == ""
        assert palette.accent == ""
        assert palette.mood == ""
        assert palette.specific_colors == []


class TestVisualAnchoring:
    """视觉锚定测试"""

    def test_create_visual_anchoring(self):
        """测试创建视觉锚定"""
        visual = VisualAnchoring(
            art_style="古风水墨",
            art_style_en="Ancient Chinese ink painting style",
            color_palette=ColorPalette(
                primary="蓝色",
                secondary="白色",
                accent="金色",
                mood="神秘",
            ),
            lighting_style="自然光",
            texture_style="细腻质感",
            atmosphere_keywords=["仙侠", "古风", "神秘"],
            atmosphere_keywords_en=["Xianxia", "Ancient", "Mystical"],
            forbidden_elements=["现代建筑", "高科技设备"],
        )

        assert visual.art_style == "古风水墨"
        assert visual.art_style_en == "Ancient Chinese ink painting style"
        assert visual.lighting_style == "自然光"
        assert "仙侠" in visual.atmosphere_keywords
        assert "现代建筑" in visual.forbidden_elements

    def test_visual_anchoring_defaults(self):
        """测试视觉锚定默认值"""
        visual = VisualAnchoring()

        assert visual.art_style == ""
        assert visual.atmosphere_keywords == []
        assert visual.forbidden_elements == []


class TestCharacterVisualRules:
    """角色视觉规则测试"""

    def test_create_character_rules(self):
        """测试创建角色视觉规则"""
        rules = CharacterVisualRules(
            face_style="东方古典面容",
            face_style_en="Eastern classical face",
            body_proportion="九头身",
            clothing_system="古装体系",
            clothing_materials="丝绸、纱、锦",
            hair_style_rules="古风发髻",
            accessory_rules="玉佩、簪子",
        )

        assert rules.face_style == "东方古典面容"
        assert rules.body_proportion == "九头身"
        assert "丝绸" in rules.clothing_materials


class TestSceneVisualRules:
    """场景视觉规则测试"""

    def test_create_scene_rules(self):
        """测试创建场景视觉规则"""
        rules = SceneVisualRules(
            architecture_style="古典中式建筑",
            landscape_style="山水意境",
            interior_style="简约雅致",
            weather_patterns="多云、雾气",
        )

        assert rules.architecture_style == "古典中式建筑"
        assert rules.landscape_style == "山水意境"
        assert rules.weather_patterns == "多云、雾气"


class TestItemVisualRules:
    """物品视觉规则测试"""

    def test_create_item_rules(self):
        """测试创建物品视觉规则"""
        rules = ItemVisualRules(
            weapon_style="古典风格",
            material_system="金属、木质、玉石",
            craftsmanship="精细工艺",
        )

        assert rules.weapon_style == "古典风格"
        assert rules.material_system == "金属、木质、玉石"
        assert rules.craftsmanship == "精细工艺"


class TestWorldBible:
    """完整世界观圣经测试"""

    def test_create_world_bible(self):
        """测试创建完整世界观圣经"""
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
                ),
                atmosphere_keywords=["仙侠", "古风"],
                forbidden_elements=["现代建筑"],
            ),
            character_visual_rules=CharacterVisualRules(
                face_style="东方古典面容",
                clothing_system="古装体系",
            ),
            scene_visual_rules=SceneVisualRules(
                architecture_style="古典中式建筑",
                landscape_style="山水意境",
            ),
            item_visual_rules=ItemVisualRules(
                weapon_style="古典风格",
                material_system="金属、木质",
            ),
        )

        assert wb.id == "wb_001"
        assert wb.novel_title == "仙侠小说"
        assert wb.world_framework.genre == "仙侠"
        assert wb.visual_anchoring.art_style == "古风水墨"
        assert wb.character_visual_rules.face_style == "东方古典面容"
        assert wb.scene_visual_rules.architecture_style == "古典中式建筑"
        assert wb.item_visual_rules.weapon_style == "古典风格"

    def test_world_bible_serialization(self):
        """测试世界观圣经序列化"""
        wb = WorldBible(
            id="wb_test",
            project_id="proj_test",
            novel_title="测试小说",
            world_framework=WorldFramework(
                genre="都市",
                era_setting="现代",
            ),
        )

        data = wb.model_dump()

        assert data['id'] == "wb_test"
        assert data['novel_title'] == "测试小说"
        assert data['world_framework']['genre'] == "都市"
        assert data['world_framework']['era_setting'] == "现代"

    def test_world_bible_deserialization(self):
        """测试世界观圣经反序列化"""
        data = {
            'id': 'wb_test',
            'project_id': 'proj_test',
            'novel_title': '测试小说',
            'world_framework': {
                'genre': '科幻',
                'sub_genre': '赛博朋克',
                'era_setting': '未来',
                'technology_level': '高科技',
                'power_system': '科技强化',
                'social_structure': '公司统治',
                'geography_overview': '未来城市',
                'key_concepts': ['AI', '虚拟现实'],
                'tone_and_mood': '冷酷、科技感',
            },
            'visual_anchoring': {
                'art_style': '赛博朋克',
                'art_style_en': 'Cyberpunk style',
                'color_palette': {
                    'primary': '霓虹色',
                    'secondary': '深蓝',
                    'accent': '紫色',
                    'mood': '科技感',
                    'specific_colors': ['#FF00FF', '#00FFFF', '#0000FF'],
                },
                'lighting_style': '霓虹灯',
                'texture_style': '金属质感',
                'atmosphere_keywords': ['科技', '未来'],
                'atmosphere_keywords_en': ['Tech', 'Future'],
                'forbidden_elements': ['自然风景'],
            },
            'character_visual_rules': {
                'face_style': '现代面容',
                'face_style_en': 'Modern face',
                'body_proportion': '标准比例',
                'clothing_system': '未来风格',
                'clothing_materials': '合成纤维',
                'hair_style_rules': '短发或染发',
                'accessory_rules': '科技配饰',
            },
            'scene_visual_rules': {
                'architecture_style': '未来建筑',
                'landscape_style': '都市景观',
                'interior_style': '科技感',
                'weather_patterns': '雾霾或雨天',
            },
            'item_visual_rules': {
                'weapon_style': '科技武器',
                'material_system': '金属、塑料',
                'craftsmanship': '工业制造',
            },
        }

        wb = WorldBible(**data)

        assert wb.id == 'wb_test'
        assert wb.world_framework.genre == '科幻'
        assert wb.visual_anchoring.art_style == '赛博朋克'
        assert wb.character_visual_rules.face_style == '现代面容'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
