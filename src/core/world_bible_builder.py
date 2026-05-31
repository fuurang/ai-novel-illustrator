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
                        "source_evidence": json.dumps(
                            {
                                "setting_evidence": framework.get("setting_evidence", []),
                                "visual_evidence": framework.get("visual_evidence", []),
                                "style_inference_notes": framework.get("style_inference_notes", []),
                            },
                            ensure_ascii=False,
                        ),
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
            "科幻": ("克制近未来写实", "Restrained near-future realistic style"),
            "历史": ("古典写实", "Classical realistic style"),
            "言情": ("现代生活写实", "Modern slice-of-life realistic style"),
            "悬疑": ("冷调现实主义", "Cold-toned realistic noir style"),
        }
        
        art_style, art_style_en = art_styles.get(genre, ("现代现实灾变写实", "Modern post-apocalyptic realistic style"))
        
        return {
            "visual_anchoring": VisualAnchoring(
                art_style=art_style,
                art_style_en=art_style_en,
                color_palette=ColorPalette(
                    primary="灰黑色",
                    secondary="水泥灰",
                    accent="警示红",
                    mood="压抑、冷峻、末日生存感",
                    specific_colors=["#111827", "#374151", "#6B7280", "#B91C1C", "#D97706", "#E5E7EB"],
                ),
                lighting_style="低照度自然光、应急灯、阴天漫射光",
                texture_style="破损水泥、金属锈蚀、灰尘、污渍、潮湿痕迹",
                atmosphere_keywords=["现代", "灾变", "压抑", "生存", "秩序崩坏"],
                atmosphere_keywords_en=["modern", "post-apocalyptic", "oppressive", "survival", "social collapse"],
                forbidden_elements=["古风服饰", "仙侠法器", "宗门建筑", "古代宫殿", "水墨仙境", "赛博朋克霓虹泛滥"],
            ),
            "character_visual_rules": CharacterVisualRules(
                face_style="现代东亚写实面孔",
                face_style_en="Modern East Asian realistic face",
                body_proportion="真实自然比例，避免夸张游戏化造型",
                clothing_system="现代日常服、户外防护服、临时拼接的生存装备",
                clothing_materials="棉布、尼龙、防水布、皮革、塑料、金属扣件",
                hair_style_rules="现代发型，灾变环境下可凌乱、油污、缺乏打理",
                accessory_rules="背包、手电、口罩、绷带、工具、简易防护装备",
            ),
            "scene_visual_rules": SceneVisualRules(
                architecture_style="现代城市建筑、小区、街道、医院、商场、地下空间，可呈现破败损毁",
                landscape_style="现代城市废墟、封锁道路、荒废街区、临时避难点",
                interior_style="现代住宅、办公室、超市、医院内部，断电后的杂乱与应急布置",
                weather_patterns="阴天、雾霾、雨后潮湿、灰尘弥漫、低能见度",
            ),
            "item_visual_rules": ItemVisualRules(
                weapon_style="现代工具、简易冷兵器、消防斧、撬棍、临时改造装备",
                material_system="金属、塑料、橡胶、玻璃、混凝土、织物",
                craftsmanship="工业量产品与临时改造痕迹并存",
            ),
        }
