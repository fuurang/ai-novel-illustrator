"""
实体提取器 - 从章节文本中提取人物、场景、物品实体
"""
from typing import Optional

from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader
from src.models.entity import Entity, EntityType
from src.models.chapter import Chapter
from src.models.world_bible import WorldBible


class EntityExtractor:
    """
    实体提取器，负责从单章文本中提取人物、场景、物品实体
    
    核心流程：
    1. 构建 WorldBible 摘要作为上下文约束
    2. 构建已有实体列表避免重复提取
    3. 调用 P03 Prompt 提取本章实体
    4. 解析返回结果为标准实体候选格式
    """
    
    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader, config: Optional[dict] = None):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.config = config or {}
        self.max_retries = self.config.get("max_retries", 3)
        self.entity_confidence_threshold = self.config.get("entity_confidence_threshold", 0.7)
        self.extraction_level = self.config.get("extraction_level", "balanced")
    
    async def extract_from_chapter(
        self,
        chapter: Chapter,
        world_bible: WorldBible,
        existing_entities: list[Entity] = None,
    ) -> list[dict]:
        """
        从单个章节中提取实体
        
        Args:
            chapter: 章节对象
            world_bible: 世界观对象
            existing_entities: 已有的实体列表（用于避免重复提取）
            
        Returns:
            实体候选字典列表
        """
        existing_entities = existing_entities or []
        wb_summary = self._summarize_world_bible(world_bible)
        existing_str = self._format_existing(existing_entities)
        
        chapter_text = chapter.text[:20000]
        
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("entity_extraction", {
                    "chapter_number": str(chapter.number),
                    "chapter_title": chapter.title,
                    "chapter_text": chapter_text,
                    "world_bible_summary": wb_summary,
                    "existing_entities": existing_str,
                    "extraction_level": self.extraction_level,
                    "extraction_level_instruction": self._extraction_level_instruction(self.extraction_level),
                })
                
                result = await self.llm.generate_json(user_prompt, system_prompt)
                
                candidates = self._parse_result(result, chapter.number)
                candidates = [
                    c for c in candidates
                    if c.get("confidence", 0) >= self.entity_confidence_threshold
                ]
                
                return candidates
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return []
        
        return []

    def _extraction_level_instruction(self, level: str) -> str:
        level = (level or "balanced").lower()
        instructions = {
            "all": (
                "【提取档位：全部】\n"
                "尽量完整提取本章所有可复用出图对象：有名角色、可识别身份的无名角色、明确地点/空间、"
                "有视觉特征或剧情用途的物品都要列出。宁可略多，但仍必须有原文依据，禁止臆造。"
            ),
            "balanced": (
                "【提取档位：适中】\n"
                "提取本章有稳定复用价值或画面表现价值的对象：主要/次要角色、当前主要场景、"
                "推动情节或具有辨识度的物品。路人、一次性泛称地点、普通背景杂物不提取。"
            ),
            "key": (
                "【提取档位：关键】\n"
                "只提取影响剧情理解、后续反复出现、或本章必须出图的关键对象：核心角色、关键场景、"
                "关键道具。临时人物、过场地点、普通物品全部忽略。"
            ),
        }
        return instructions.get(level, instructions["balanced"])
    
    def _summarize_world_bible(self, wb: WorldBible) -> str:
        """
        格式化 WorldBible 为摘要字符串
        
        Args:
            wb: 世界观对象
            
        Returns:
            格式化的摘要字符串
        """
        forbidden = ", ".join(wb.visual_anchoring.forbidden_elements) if wb.visual_anchoring.forbidden_elements else "无"
        
        return (
            f"类型: {wb.world_framework.genre} | "
            f"子类型: {wb.world_framework.sub_genre} | "
            f"时代: {wb.world_framework.era_setting} | "
            f"力量体系: {wb.world_framework.power_system} | "
            f"禁止元素: {forbidden}"
        )
    
    def _format_existing(self, entities: list[Entity]) -> str:
        """
        格式化已有实体列表
        
        Args:
            entities: 已有实体列表
            
        Returns:
            格式化的实体列表字符串
        """
        if not entities:
            return "（无已有实体）"
        
        lines = []
        type_labels = {
            EntityType.CHARACTER: "角色",
            EntityType.SCENE: "场景",
            EntityType.ITEM: "物品",
            EntityType.CREATURE: "生物",
        }
        
        for entity in entities:
            type_label = type_labels.get(entity.type, "未知")
            aliases = ", ".join(entity.aliases) if entity.aliases else "无"
            lines.append(f"- [{type_label}] {entity.name} (别名: {aliases})")
        
        return "\n".join(lines)
    
    def _parse_result(self, result: dict, chapter_number: int) -> list[dict]:
        """
        解析 LLM 返回结果为标准实体候选格式
        
        Args:
            result: LLM 返回的原始字典
            chapter_number: 章节编号
            
        Returns:
            实体候选字典列表
        """
        candidates = []
        
        for char in result.get("characters", []):
            candidates.append({
                "name": char.get("name", ""),
                "aliases": char.get("aliases", []),
                "type": "character",
                "brief_description": char.get("brief_description", ""),
                "source_quote": char.get("source_quote", ""),
                "confidence": char.get("confidence", 0.8),
                "is_new": char.get("is_new", True),
                "chapter": chapter_number,
                "location": f"第{chapter_number}章",
                "context": char.get("context", ""),
                "appearance_note": char.get("appearance_note", ""),
                "clothing_override": char.get("clothing_override", ""),
            })
        
        for scene in result.get("scenes", []):
            candidates.append({
                "name": scene.get("name", ""),
                "aliases": [],
                "type": "scene",
                "brief_description": scene.get("brief_description", ""),
                "source_quote": scene.get("source_quote", ""),
                "confidence": scene.get("confidence", 0.8),
                "is_new": scene.get("is_new", True),
                "chapter": chapter_number,
                "location": f"第{chapter_number}章",
                "context": scene.get("context", ""),
                "appearance_note": scene.get("appearance_note", ""),
                "clothing_override": "",
            })
        
        for item in result.get("items", []):
            candidates.append({
                "name": item.get("name", ""),
                "aliases": [],
                "type": "item",
                "category": item.get("category", ""),
                "brief_description": item.get("brief_description", ""),
                "source_quote": item.get("source_quote", ""),
                "confidence": item.get("confidence", 0.8),
                "is_new": item.get("is_new", True),
                "chapter": chapter_number,
                "location": f"第{chapter_number}章",
                "context": item.get("context", ""),
                "appearance_note": item.get("appearance_note", ""),
                "clothing_override": "",
            })
        
        return candidates
