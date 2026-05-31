"""
属性构建器 - 基于实体和原文引用提取完整视觉属性
"""
import json
from typing import Optional

from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader
from src.models.entity import Entity, EntityType, SourceQuote, WorldBinding
from src.models.world_bible import WorldBible


class AttributeBuilder:
    """
    属性构建器，负责基于实体和原文引用提取完整的视觉属性
    
    核心流程：
    1. 根据实体类型选择提取方法（角色/场景/物品）
    2. 构建 Prompt 输入（包含 WorldBible 视觉规则和原文引用）
    3. 调用对应的 Prompt（P05/P06/P07）提取属性
    4. 更新实体的 attributes 和 world_binding 字段
    """
    
    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader, max_retries: int = 3):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.max_retries = max_retries
    
    async def build_attributes(
        self,
        entity: Entity,
        world_bible: WorldBible,
    ) -> Entity:
        """
        为实体构建完整的视觉属性
        
        Args:
            entity: 实体对象
            world_bible: 世界观对象
            
        Returns:
            更新后的实体对象
        """
        if entity.type == EntityType.CHARACTER:
            return await self._build_character(entity, world_bible)
        elif entity.type == EntityType.SCENE:
            return await self._build_scene(entity, world_bible)
        elif entity.type == EntityType.ITEM:
            return await self._build_item(entity, world_bible)
        
        return entity
    
    async def _build_character(self, entity: Entity, wb: WorldBible) -> Entity:
        """
        提取角色属性
        
        Args:
            entity: 角色实体
            wb: 世界观对象
            
        Returns:
            更新后的角色实体
        """
        visual_rules = {
            "face_style": wb.character_visual_rules.face_style,
            "face_style_en": wb.character_visual_rules.face_style_en,
            "clothing_system": wb.character_visual_rules.clothing_system,
            "clothing_materials": wb.character_visual_rules.clothing_materials,
            "hair_style_rules": wb.character_visual_rules.hair_style_rules,
            "accessory_rules": wb.character_visual_rules.accessory_rules,
            "art_style": wb.visual_anchoring.art_style,
        }
        
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("character_attribute", {
                    "character_name": entity.name,
                    "source_quotes": self._format_quotes(entity.source_quotes),
                    "world_bible_visual_rules": json.dumps(visual_rules, ensure_ascii=False),
                })
                
                result = await self.llm.generate_json_async(user_prompt, system_prompt)
                
                entity.attributes = result.get("attributes", {})
                entity.world_binding = WorldBinding(
                    genre=wb.world_framework.genre,
                    era=wb.world_framework.era_setting,
                    face_style=wb.character_visual_rules.face_style,
                    clothing_system=wb.character_visual_rules.clothing_system,
                    art_style=wb.visual_anchoring.art_style,
                )
                
                return entity
                
            except Exception:
                if attempt == self.max_retries - 1:
                    entity.attributes = self._get_default_character_attributes()
        
        return entity
    
    async def _build_scene(self, entity: Entity, wb: WorldBible) -> Entity:
        """
        提取场景属性
        
        Args:
            entity: 场景实体
            wb: 世界观对象
            
        Returns:
            更新后的场景实体
        """
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("scene_attribute", {
                    "scene_name": entity.name,
                    "source_quotes": self._format_quotes(entity.source_quotes),
                    "world_bible_scene_rules": json.dumps(wb.scene_visual_rules.model_dump(), ensure_ascii=False),
                })
                
                result = await self.llm.generate_json_async(user_prompt, system_prompt)
                entity.attributes = result.get("attributes", {})
                return entity
                
            except Exception:
                if attempt == self.max_retries - 1:
                    entity.attributes = self._get_default_scene_attributes()
        
        return entity
    
    async def _build_item(self, entity: Entity, wb: WorldBible) -> Entity:
        """
        提取物品属性
        
        Args:
            entity: 物品实体
            wb: 世界观对象
            
        Returns:
            更新后的物品实体
        """
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("item_attribute", {
                    "item_name": entity.name,
                    "source_quotes": self._format_quotes(entity.source_quotes),
                    "world_bible_item_rules": json.dumps(wb.item_visual_rules.model_dump(), ensure_ascii=False),
                })
                
                result = await self.llm.generate_json_async(user_prompt, system_prompt)
                entity.attributes = result.get("attributes", {})
                return entity
                
            except Exception:
                if attempt == self.max_retries - 1:
                    entity.attributes = self._get_default_item_attributes()
        
        return entity
    
    def _format_quotes(self, quotes: list[SourceQuote]) -> str:
        """
        格式化原文引用列表
        
        Args:
            quotes: 原文引用列表
            
        Returns:
            格式化的字符串
        """
        if not quotes:
            return "（无原文引用）"
        
        lines = []
        for q in quotes:
            location = q.location or f"第{q.chapter}章"
            lines.append(f"- [{location}] {q.text}")
        
        return "\n".join(lines)
    
    def _get_default_character_attributes(self) -> dict:
        """获取默认角色属性"""
        return {
            "gender": "未知",
            "age_range": "成年",
            "appearance": {
                "face": "标准面容",
                "hair": "黑色长发",
                "body": "标准身材",
                "distinguishing_features": "无特别标志",
            },
            "clothing": {
                "default": "符合时代背景的服饰",
                "variations": [],
            },
            "personality": "性格特征待补充",
            "abilities": [],
            "relationships": [],
        }
    
    def _get_default_scene_attributes(self) -> dict:
        """获取默认场景属性"""
        return {
            "environment_type": "室内/室外",
            "time_of_day": "白天",
            "weather": "晴朗",
            "visual_description": "场景描述待补充",
            "atmosphere": "一般",
            "key_landmarks": [],
            "color_palette": "基础色调",
        }
    
    def _get_default_item_attributes(self) -> dict:
        """获取默认物品属性"""
        return {
            "category": "其他",
            "visual_description": "物品描述待补充",
            "material": "普通材质",
            "size": "普通大小",
            "special_effects": "无",
            "owner": "",
        }
