"""
世界观的Pydantic数据模型
定义小说世界观框架、视觉锚定等数据结构
"""

from pydantic import BaseModel, Field
from datetime import datetime


class WorldFramework(BaseModel):
    """世界观框架"""
    genre: str = ""
    sub_genre: str = ""
    era_setting: str = ""
    technology_level: str = ""
    power_system: str = ""
    social_structure: str = ""
    geography_overview: str = ""
    key_concepts: list[str] = []
    tone_and_mood: str = ""


class ColorPalette(BaseModel):
    """色彩调色板"""
    primary: str = ""
    secondary: str = ""
    accent: str = ""
    mood: str = ""
    specific_colors: list[str] = []


class VisualAnchoring(BaseModel):
    """视觉锚定"""
    art_style: str = ""
    art_style_en: str = ""
    color_palette: ColorPalette = ColorPalette()
    lighting_style: str = ""
    texture_style: str = ""
    atmosphere_keywords: list[str] = []
    atmosphere_keywords_en: list[str] = []
    forbidden_elements: list[str] = []


class CharacterVisualRules(BaseModel):
    """角色视觉规则"""
    face_style: str = ""
    face_style_en: str = ""
    body_proportion: str = ""
    clothing_system: str = ""
    clothing_materials: str = ""
    hair_style_rules: str = ""
    accessory_rules: str = ""


class SceneVisualRules(BaseModel):
    """场景视觉规则"""
    architecture_style: str = ""
    landscape_style: str = ""
    interior_style: str = ""
    weather_patterns: str = ""


class ItemVisualRules(BaseModel):
    """物品视觉规则"""
    weapon_style: str = ""
    material_system: str = ""
    craftsmanship: str = ""


class WorldBible(BaseModel):
    """完整的世界观锚定文档"""
    id: str = ""
    project_id: str = ""
    novel_title: str = ""
    world_framework: WorldFramework = WorldFramework()
    visual_anchoring: VisualAnchoring = VisualAnchoring()
    character_visual_rules: CharacterVisualRules = CharacterVisualRules()
    scene_visual_rules: SceneVisualRules = SceneVisualRules()
    item_visual_rules: ItemVisualRules = ItemVisualRules()
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
