"""
世界观构建器 - 分析小说文本生成世界观框架和视觉锚定
"""
import json
import uuid
from typing import Optional

from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader
from src.models.world_bible import (
    WorldBible,
    WorldFramework,
    VisualAnchoring,
    ColorPalette,
    CharacterVisualRules,
    SceneVisualRules,
    ItemVisualRules,
)


class WorldBibleBuilder:
    """
    世界观构建器，负责从小说文本中提取世界观框架并生成视觉锚定规范
    
    核心流程：
    1. 调用 P01 Prompt 分析世界观框架
    2. 调用 P02 Prompt 生成视觉锚定规范
    3. 合并输出完整的 WorldBible 对象
    """
    
    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader, max_retries: int = 3):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.max_retries = max_retries
    
    async def analyze(self, text: str, novel_title: str = "", project_id: str = "") -> WorldBible:
        """
        分析小说文本，生成完整的 WorldBible
        
        Args:
            text: 小说文本（前几章的内容效果最佳）
            novel_title: 小说标题
            project_id: 项目ID
            
        Returns:
            完整的 WorldBible 对象
        """
        framework = await self._analyze_framework(text, novel_title)
        visual_data = await self._generate_visual_anchoring(framework, novel_title)
        
        return WorldBible(
            id=str(uuid.uuid4())[:8],
            project_id=project_id,
            novel_title=novel_title,
            world_framework=WorldFramework(**framework),
            visual_anchoring=visual_data["visual_anchoring"],
            character_visual_rules=visual_data["character_visual_rules"],
            scene_visual_rules=visual_data["scene_visual_rules"],
            item_visual_rules=visual_data["item_visual_rules"],
        )
    
    async def _analyze_framework(self, text: str, novel_title: str) -> dict:
        """
        调用 P01 Prompt 分析世界观框架
        
        Args:
            text: 小说文本
            novel_title: 小说标题
            
        Returns:
            世界观框架字典
        """
        text_content = text[:30000]
        
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render(
                    "world_bible_analyze",
                    {"novel_title": novel_title, "text_content": text_content},
                )
                result = await self.llm.generate_json(user_prompt, system_prompt)
                
                required_fields = ["genre", "era_setting", "power_system"]
                if all(result.get(f) for f in required_fields):
                    return result
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return self._get_default_framework(novel_title)
        
        return self._get_default_framework(novel_title)
    
    async def _generate_visual_anchoring(self, framework: dict, novel_title: str) -> dict:
        """
        调用 P02 Prompt 生成视觉锚定规范
        
        Args:
            framework: 世界观框架字典
            novel_title: 小说标题
            
        Returns:
            包含所有视觉规则的数据字典
        """
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render(
                    "visual_anchoring",
                    {
                        "novel_title": novel_title,
                        "world_framework": json.dumps(framework, ensure_ascii=False),
                    },
                )
                result = await self.llm.generate_json(user_prompt, system_prompt)
                
                visual_anchoring_data = result.get("visual_anchoring", {})
                color_palette_data = visual_anchoring_data.get("color_palette", {})
                
                visual_anchoring = VisualAnchoring(
                    art_style=visual_anchoring_data.get("art_style", ""),
                    art_style_en=visual_anchoring_data.get("art_style_en", ""),
                    color_palette=ColorPalette(**color_palette_data),
                    lighting_style=visual_anchoring_data.get("lighting_style", ""),
                    texture_style=visual_anchoring_data.get("texture_style", ""),
                    atmosphere_keywords=visual_anchoring_data.get("atmosphere_keywords", []),
                    atmosphere_keywords_en=visual_anchoring_data.get("atmosphere_keywords_en", []),
                    forbidden_elements=visual_anchoring_data.get("forbidden_elements", []),
                )
                
                character_visual_rules = CharacterVisualRules(
                    **result.get("character_visual_rules", {})
                )
                
                scene_visual_rules = SceneVisualRules(
                    **result.get("scene_visual_rules", {})
                )
                
                item_visual_rules = ItemVisualRules(
                    **result.get("item_visual_rules", {})
                )
                
                return {
                    "visual_anchoring": visual_anchoring,
                    "character_visual_rules": character_visual_rules,
                    "scene_visual_rules": scene_visual_rules,
                    "item_visual_rules": item_visual_rules,
                }
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return self._get_default_visual_anchoring(framework.get("genre", ""))
        
        return self._get_default_visual_anchoring(framework.get("genre", ""))
    
    def _get_default_framework(self, novel_title: str) -> dict:
        """
        获取默认世界观框架（当LLM调用失败时使用）
        
        Args:
            novel_title: 小说标题
            
        Returns:
            默认世界观框架
        """
        return {
            "genre": "其他",
            "sub_genre": "",
            "era_setting": "现代",
            "technology_level": "现代科技水平",
            "power_system": "无超自然力量体系",
            "social_structure": "现代社会结构",
            "geography_overview": "现代城市",
            "key_concepts": [],
            "tone_and_mood": "现实主义",
        }
    
    def _get_default_visual_anchoring(self, genre: str) -> dict:
        """
        获取默认视觉锚定规范（当LLM调用失败时使用）
        
        Args:
            genre: 小说类型
            
        Returns:
            默认视觉锚定规范
        """
        art_styles = {
            "仙侠": ("古风水墨", "Ancient Chinese ink painting style"),
            "玄幻": ("奇幻写实", "Fantasy realistic style"),
            "都市": ("现代写实", "Modern realistic photography style"),
            "科幻": ("赛博朋克", "Cyberpunk style"),
            "历史": ("古典写实", "Classical realistic style"),
            "言情": ("小清新", "Soft pastel style"),
            "悬疑": ("暗色调", "Dark noir style"),
        }
        
        art_style, art_style_en = art_styles.get(genre, ("通用风格", "General style"))
        
        return {
            "visual_anchoring": VisualAnchoring(
                art_style=art_style,
                art_style_en=art_style_en,
                color_palette=ColorPalette(
                    primary="蓝色",
                    secondary="白色",
                    accent="金色",
                    mood="清爽",
                    specific_colors=["#FFFFFF", "#87CEEB", "#F5F5DC", "#DAA520", "#2F4F4F", "#8B4513"],
                ),
                lighting_style="自然光",
                texture_style="细腻质感",
                atmosphere_keywords=["清新", "自然", "和谐"],
                atmosphere_keywords_en=["fresh", "natural", "harmonious"],
                forbidden_elements=["现代建筑", "高科技设备", "西方风格"],
            ),
            "character_visual_rules": CharacterVisualRules(
                face_style="东方古典面容",
                face_style_en="Eastern classical face",
                body_proportion="标准比例",
                clothing_system="符合时代背景的服饰",
                clothing_materials="丝绸、棉麻",
                hair_style_rules="符合时代背景的发型",
                accessory_rules="简约配饰",
            ),
            "scene_visual_rules": SceneVisualRules(
                architecture_style="古典中式建筑",
                landscape_style="山水意境",
                interior_style="简约雅致",
                weather_patterns="多变天气",
            ),
            "item_visual_rules": ItemVisualRules(
                weapon_style="古典风格",
                material_system="金属、木质",
                craftsmanship="精细工艺",
            ),
        }
