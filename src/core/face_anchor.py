"""
面部锚定图生成器
生成角色的面部锚定图（正面特写），用于后续面部一致性生图

关键流程：
1. 使用 face_anchor_prompt.yaml 模板生成专用提示词
2. 调用 ChatGPT2API 的 text_to_image 生成正面面部特写
3. 保存面部锚定图到 face_anchors/ 目录
4. 后续所有该角色的生图都通过 edit_image 接口引用此锚定图
"""

import json
from pathlib import Path
from src.llm.adapter import LLMAdapter
from src.llm.prompt_loader import PromptLoader
from src.models.entity import Entity
from src.models.prompt import Prompt
from src.models.world_bible import WorldBible
from src.render.chatgpt2api_backend import ChatGPT2APIBackend


class FaceAnchorGenerator:
    """
    面部锚定图生成器类
    
    负责生成角色的面部锚定图，为后续的面部一致性生图提供基础
    """

    def __init__(
        self,
        llm: LLMAdapter,
        prompt_loader: PromptLoader,
        image_backend: ChatGPT2APIBackend,
    ):
        """
        初始化面部锚定图生成器
        
        Args:
            llm: LLM 适配器实例（用于生成面部锚定图专用提示词）
            prompt_loader: 提示词加载器实例
            image_backend: 图片生成后端实例
        """
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.backend = image_backend

    async def generate(
        self,
        entity: Entity,
        character_prompt: Prompt,
        world_bible: WorldBible,
        output_dir: str,
    ) -> tuple[str, str]:
        """
        生成角色面部锚定图

        Args:
            entity: 角色实体
            character_prompt: 角色提示词
            world_bible: 世界观锚定文档
            output_dir: 输出目录

        Returns:
            tuple[str, str]: (image_path, face_prompt_text)
                - image_path: 生成的锚定图路径
                - face_prompt_text: 使用的面部提示词

        Raises:
            Exception: 生成失败时抛出异常
        """
        face_prompt = self._generate_face_prompt(entity, character_prompt, world_bible)
        
        image_bytes = await self.backend.generate_face_anchor(face_prompt)
        
        output_path = Path(output_dir) / "face_anchors" / f"{entity.id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return str(output_path), face_prompt

    def _generate_face_prompt(
        self,
        entity: Entity,
        character_prompt: Prompt,
        world_bible: WorldBible,
    ) -> str:
        """
        生成面部锚定图专用提示词
        
        优先使用 face_anchor_prompt.yaml 模板生成，如果没有则使用角色提示词的面容块

        Args:
            entity: 角色实体
            character_prompt: 角色提示词
            world_bible: 世界观锚定文档

        Returns:
            str: 英文提示词
        """
        try:
            system, user = self.prompt_loader.render("face_anchor_prompt", {
                "character_name": entity.name,
                "face_block_chinese": character_prompt.face_block_chinese,
                "face_block_english": character_prompt.face_block_english,
                "world_bible_face_style": world_bible.character_visual_rules.face_style_en,
            })
            
            import asyncio
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.llm.generate_json(user, system))
            return result.get("english_prompt", character_prompt.english_prompt)
        except FileNotFoundError:
            return character_prompt.english_prompt
        except Exception:
            return character_prompt.english_prompt

    async def generate_from_description(
        self,
        entity: Entity,
        face_description: str,
        output_dir: str,
        size: str = "1024x1024",
    ) -> str:
        """
        从面部描述直接生成锚定图（不经过 LLM 提示词生成）

        Args:
            entity: 角色实体
            face_description: 面部描述文本（英文效果更佳）
            output_dir: 输出目录
            size: 图片尺寸，默认 1024x1024

        Returns:
            str: 生成的锚定图路径
        """
        image_bytes = await self.backend.generate_face_anchor(face_description, size=size)
        
        output_path = Path(output_dir) / "face_anchors" / f"{entity.id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return str(output_path)

    async def batch_generate(
        self,
        entities: list[Entity],
        prompts: list[Prompt],
        world_bible: WorldBible,
        output_dir: str,
    ) -> dict[str, str]:
        """
        批量生成多个角色的面部锚定图

        Args:
            entities: 角色实体列表
            prompts: 角色提示词列表
            world_bible: 世界观锚定文档
            output_dir: 输出目录

        Returns:
            dict[str, str]: entity_id -> image_path 的映射
        """
        prompt_map = {p.entity_id: p for p in prompts}
        results = {}
        
        for entity in entities:
            if entity.type.value != "character":
                continue
                
            prompt = prompt_map.get(entity.id)
            if not prompt:
                continue
                
            try:
                image_path, _ = await self.generate(entity, prompt, world_bible, output_dir)
                results[entity.id] = image_path
            except Exception as e:
                print(f"生成 {entity.name} 面部锚定图失败: {e}")
                continue
        
        return results

    def get_face_anchor_path(self, entity_id: str, face_anchor_dir: str) -> str:
        """
        获取角色的面部锚定图路径

        Args:
            entity_id: 角色ID
            face_anchor_dir: 面部锚定图目录

        Returns:
            str: 锚定图路径，如果不存在则返回空字符串
        """
        path = Path(face_anchor_dir) / f"{entity_id}.png"
        return str(path) if path.exists() else ""
