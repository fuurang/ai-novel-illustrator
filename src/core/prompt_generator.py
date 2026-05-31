"""
提示词生成器 - 基于实体属性和世界观生成AI绘画提示词
"""
import json
import uuid
from typing import Optional

from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader
from src.models.entity import Entity, EntityType, SourceQuote, ChapterAppearance
from src.models.prompt import Prompt, PromptParameters
from src.models.world_bible import WorldBible


class PromptGenerator:
    """
    提示词生成器，负责基于实体属性和世界观生成AI绘画提示词
    
    核心功能：
    1. 根据实体类型（角色/场景/物品）选择对应的生成方法
    2. 调用对应的 Prompt（P09/P10/P11）生成提示词
    3. 将 LLM 输出转换为标准的 Prompt 对象
    4. 生成中文和英文双版本提示词
    """
    
    def __init__(self, llm: LLMAdapter, prompt_loader: PromptLoader, config: Optional[dict] = None):
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.config = config or {}
        self.max_retries = self.config.get("max_retries", 3)
        self.include_negative = self.config.get("include_negative", True)
    
    async def generate(
        self,
        entity: Entity,
        world_bible: WorldBible,
        chapter_indices: list[int] | None = None,
    ) -> list[Prompt]:
        """
        为实体生成AI绘画提示词
        
        Args:
            entity: 实体对象
            world_bible: 世界观对象
            chapter_indices: 章节索引列表，用于生成变体提示词
            
        Returns:
            Prompt 对象列表
        """
        if entity.type == EntityType.CHARACTER:
            base_prompt = await self._generate_character(entity, world_bible)
        elif entity.type == EntityType.SCENE:
            base_prompt = await self._generate_scene(entity, world_bible)
        elif entity.type == EntityType.ITEM:
            base_prompt = await self._generate_item(entity, world_bible)
        else:
            base_prompt = self._create_empty_prompt(entity)

        prompts = []

        if chapter_indices and entity.chapter_appearances:
            for ch_idx in chapter_indices:
                prompt_copy = base_prompt.model_copy()
                prompt_copy.chapter_number = ch_idx
                appearance = self._find_appearance(entity, ch_idx)
                if appearance and appearance.clothing_override:
                    prompt_copy.variant_label = f"第{ch_idx}章-{appearance.clothing_override}"
                    prompt_copy.chinese_prompt = self._apply_clothing_override(
                        prompt_copy.chinese_prompt, appearance.clothing_override
                    )
                else:
                    prompt_copy.variant_label = f"第{ch_idx}章"
                prompts.append(prompt_copy)
        else:
            if chapter_indices:
                base_prompt.chapter_number = chapter_indices[0]
            prompts.append(base_prompt)

        return prompts

    def _find_appearance(self, entity: Entity, chapter_number: int) -> ChapterAppearance | None:
        for ca in entity.chapter_appearances:
            if ca.chapter == chapter_number:
                return ca
        return None

    def _apply_clothing_override(self, prompt_text: str, clothing_override: str) -> str:
        if not clothing_override or not prompt_text:
            return prompt_text
        return prompt_text + f"，{clothing_override}"
    
    async def _generate_character(self, entity: Entity, wb: WorldBible) -> Prompt:
        """
        生成角色提示词
        
        Args:
            entity: 角色实体
            wb: 世界观对象
            
        Returns:
            角色 Prompt 对象
        """
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("character_prompt", {
                    "entity_json": json.dumps(entity.model_dump(), ensure_ascii=False, indent=2),
                    "world_bible_visual_anchoring": json.dumps(
                        self._build_world_context(wb, "character"),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "source_quotes": self._format_quotes(entity.source_quotes),
                })
                
                result = await self.llm.generate_json_async(user_prompt, system_prompt)
                return self._to_prompt(result, entity, "character", "3:4")
                
            except Exception:
                if attempt == self.max_retries - 1:
                    return self._create_default_character_prompt(entity, wb)
        
        return self._create_default_character_prompt(entity, wb)
    
    async def _generate_scene(self, entity: Entity, wb: WorldBible) -> Prompt:
        """
        生成场景提示词
        
        Args:
            entity: 场景实体
            wb: 世界观对象
            
        Returns:
            场景 Prompt 对象
        """
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("scene_prompt", {
                    "entity_json": json.dumps(entity.model_dump(), ensure_ascii=False, indent=2),
                    "world_bible_visual_anchoring": json.dumps(
                        self._build_world_context(wb, "scene"),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "world_bible_scene_rules": json.dumps(wb.scene_visual_rules.model_dump(), ensure_ascii=False),
                    "source_quotes": self._format_quotes(entity.source_quotes),
                })
                
                result = await self.llm.generate_json_async(user_prompt, system_prompt)
                return self._to_prompt(result, entity, "scene", "16:9")
                
            except Exception:
                if attempt == self.max_retries - 1:
                    return self._create_default_scene_prompt(entity, wb)
        
        return self._create_default_scene_prompt(entity, wb)
    
    async def _generate_item(self, entity: Entity, wb: WorldBible) -> Prompt:
        """
        生成物品提示词
        
        Args:
            entity: 物品实体
            wb: 世界观对象
            
        Returns:
            物品 Prompt 对象
        """
        for attempt in range(self.max_retries):
            try:
                system_prompt, user_prompt = self.prompt_loader.render("item_prompt", {
                    "entity_json": json.dumps(entity.model_dump(), ensure_ascii=False, indent=2),
                    "world_bible_visual_anchoring": json.dumps(
                        self._build_world_context(wb, "item"),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "world_bible_item_rules": json.dumps(wb.item_visual_rules.model_dump(), ensure_ascii=False),
                    "source_quotes": self._format_quotes(entity.source_quotes),
                })
                
                result = await self.llm.generate_json_async(user_prompt, system_prompt)
                return self._to_prompt(result, entity, "item", "1:1")
                
            except Exception:
                if attempt == self.max_retries - 1:
                    return self._create_default_item_prompt(entity, wb)
        
        return self._create_default_item_prompt(entity, wb)
    
    def _to_prompt(self, result: dict, entity: Entity, prompt_type: str, default_ar: str) -> Prompt:
        """
        将 LLM 输出转换为 Prompt 对象
        
        Args:
            result: LLM 返回的字典
            entity: 实体对象
            prompt_type: 提示词类型
            default_ar: 默认宽高比
            
        Returns:
            Prompt 对象
        """
        params = result.get("parameters", {})
        
        return Prompt(
            id=str(uuid.uuid4())[:8],
            entity_id=entity.id,
            type=prompt_type,
            world_prefix_chinese=result.get("world_prefix_chinese", ""),
            face_block_chinese=result.get("face_block_chinese", ""),
            chinese_prompt=result.get("chinese_prompt", ""),
            negative_prompt=result.get("negative_prompt", ""),
            style_tags=result.get("style_tags", []),
            parameters=PromptParameters(
                aspect_ratio=params.get("aspect_ratio", default_ar),
                steps=params.get("steps", 30),
                cfg_scale=params.get("cfg_scale", 7.0),
                sampler=params.get("sampler", "DPM++ 2M Karras"),
            ),
            source_quotes=[{"chapter": q.chapter, "text": q.text, "location": q.location} for q in entity.source_quotes],
        )

    def _build_world_context(self, wb: WorldBible, prompt_type: str) -> dict:
        context = {
            "visual_anchoring": wb.visual_anchoring.model_dump(),
            "world_framework": wb.world_framework.model_dump(),
            "user_worldview_text": wb.user_worldview_text,
        }

        if prompt_type == "character":
            context["character_visual_rules"] = wb.character_visual_rules.model_dump()
        elif prompt_type == "scene":
            context["scene_visual_rules"] = wb.scene_visual_rules.model_dump()
        elif prompt_type == "item":
            context["item_visual_rules"] = wb.item_visual_rules.model_dump()

        return context
    
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
    
    def _create_empty_prompt(self, entity: Entity) -> Prompt:
        """创建空的 Prompt 对象"""
        return Prompt(
            id=str(uuid.uuid4())[:8],
            entity_id=entity.id,
            type=entity.type.value,
        )
    
    def _create_default_character_prompt(self, entity: Entity, wb: WorldBible) -> Prompt:
        """创建默认的角色提示词"""
        attrs = entity.attributes or {}
        appearance = attrs.get("appearance", {})
        
        face_desc = appearance.get("face", "")
        hair_desc = appearance.get("hair", "")
        clothing_desc = attrs.get("clothing", {}).get("default", "")
        
        world_prefix = f"[{wb.visual_anchoring.art_style}]{' '.join(wb.visual_anchoring.atmosphere_keywords)}"
        face_block = f"{face_desc} {hair_desc} （面容锁定：此面容在所有图中保持一致）"
        
        chinese = f"{world_prefix} [角色] {entity.name}，{face_desc}，{clothing_desc}，{hair_desc}"
        
        negative = f"{', '.join(wb.visual_anchoring.forbidden_elements)}, 低质量, 模糊, 变形"
        
        return Prompt(
            id=str(uuid.uuid4())[:8],
            entity_id=entity.id,
            type="character",
            world_prefix_chinese=world_prefix,
            face_block_chinese=face_block,
            chinese_prompt=chinese,
            negative_prompt=negative,
            style_tags=wb.visual_anchoring.atmosphere_keywords,
            parameters=PromptParameters(aspect_ratio="3:4"),
        )
    
    def _create_default_scene_prompt(self, entity: Entity, wb: WorldBible) -> Prompt:
        """创建默认的场景提示词"""
        attrs = entity.attributes or {}
        visual_desc = attrs.get("visual_description", "")
        key_landmarks = attrs.get("key_landmarks", [])
        
        world_prefix = f"[{wb.visual_anchoring.art_style}]{' '.join(wb.visual_anchoring.atmosphere_keywords)}"
        landmarks_str = " ".join(key_landmarks) if key_landmarks else ""
        
        chinese = f"{world_prefix} [场景] {entity.name}，{visual_desc} {landmarks_str}"
        
        negative = f"{', '.join(wb.visual_anchoring.forbidden_elements)}, 人物, 低质量"
        
        return Prompt(
            id=str(uuid.uuid4())[:8],
            entity_id=entity.id,
            type="scene",
            world_prefix_chinese=world_prefix,
            chinese_prompt=chinese,
            negative_prompt=negative,
            style_tags=wb.visual_anchoring.atmosphere_keywords,
            parameters=PromptParameters(aspect_ratio="16:9"),
        )
    
    def _create_default_item_prompt(self, entity: Entity, wb: WorldBible) -> Prompt:
        """创建默认的物品提示词"""
        attrs = entity.attributes or {}
        visual_desc = attrs.get("visual_description", "")
        material = attrs.get("material", "")
        
        world_prefix = f"[{wb.visual_anchoring.art_style}]"
        
        chinese = f"{world_prefix} [物品] {entity.name}，{visual_desc}，材质：{material}"
        
        negative = f"{', '.join(wb.visual_anchoring.forbidden_elements)}, 低质量, 模糊"
        
        return Prompt(
            id=str(uuid.uuid4())[:8],
            entity_id=entity.id,
            type="item",
            world_prefix_chinese=world_prefix,
            chinese_prompt=chinese,
            negative_prompt=negative,
            style_tags=wb.visual_anchoring.atmosphere_keywords,
            parameters=PromptParameters(aspect_ratio="1:1"),
        )
