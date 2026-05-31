"""
图片生成器
基于面部锚定图生成各类图片（角色全身图、场景背景图、物品设定图）

核心原理：
- 面部锚定图 (PNG) + 角色全身提示词 → /v1/images/edits → 保持面部的全身图
- ChatGPT2API 的图片编辑接口会参考输入图片的视觉特征，在生成新图时保持一致性
- 这比 ComfyUI 的 IP-Adapter 方案更简单，无需 GPU，无需训练
"""

import asyncio
from pathlib import Path
from typing import Union
from src.models.entity import Entity, EntityType
from src.models.prompt import Prompt
from src.models.world_bible import WorldBible
from src.render.chatgpt2api_backend import ChatGPT2APIBackend


class ImageGenerator:
    """
    图片生成器类
    
    基于面部锚定图和提示词生成各类图片
    支持角色全身图、场景背景图、物品设定图等
    """

    def __init__(self, backend: ChatGPT2APIBackend, config: dict = None):
        """
        初始化图片生成器
        
        Args:
            backend: 图片生成后端实例（ChatGPT2APIBackend）
            config: 配置字典（可选），包含：
                - default_sizes: 默认尺寸配置
                - retry_on_failure: 失败时是否重试
        """
        self.backend = backend
        self.config = config or {}
        self.default_sizes = self.config.get("default_sizes", {
            "character": "1024x1536",
            "scene": "1536x1024",
            "item": "1024x1024",
            "face_anchor": "1024x1024",
        })
        image_config = self.config.get("image", self.config)
        self.max_parallel = int(image_config.get("max_parallel", 3) or 3)

    async def generate_character(
        self,
        entity: Entity,
        prompt: Prompt,
        face_anchor_path: str,
        output_dir: str,
        size: str = "1024x1536",
    ) -> str:
        """
        基于面部锚定图生成角色全身图

        Args:
            entity: 角色实体
            prompt: 角色提示词
            face_anchor_path: 面部锚定图路径
            output_dir: 输出目录
            size: 输出尺寸，默认 1024x1536（竖版角色图）

        Returns:
            str: 生成图路径

        Raises:
            FileNotFoundError: 面部锚定图不存在时抛出异常
            Exception: 生成失败时抛出异常
        """
        face_anchor_bytes = Path(face_anchor_path).read_bytes()
        
        image_bytes = await self.backend.generate_character_with_face(
            character_prompt=prompt.chinese_prompt,
            face_anchor_bytes=face_anchor_bytes,
            size=size,
        )
        
        output_path = Path(output_dir) / "characters" / f"{entity.id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return str(output_path)

    async def generate_scene(
        self,
        entity: Entity,
        prompt: Prompt,
        style_reference_path: Union[str, None] = None,
        output_dir: str = "",
        size: str = "1536x1024",
    ) -> str:
        """
        生成场景背景图

        如果有风格参考图（如第一张场景图），通过 edit_image 保持画风统一

        Args:
            entity: 场景实体
            prompt: 场景提示词
            style_reference_path: 风格参考图路径（可选）
            output_dir: 输出目录
            size: 输出尺寸，默认 1536x1024（横版场景图）

        Returns:
            str: 生成图路径

        Raises:
            Exception: 生成失败时抛出异常
        """
        style_ref = None
        if style_reference_path and Path(style_reference_path).exists():
            style_ref = Path(style_reference_path).read_bytes()

        image_bytes = await self.backend.generate_scene(
            scene_prompt=prompt.chinese_prompt,
            style_reference=style_ref,
            size=size,
        )
        
        output_path = Path(output_dir) / "scenes" / f"{entity.id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return str(output_path)

    async def generate_character_without_face(
        self,
        entity: Entity,
        prompt: Prompt,
        output_dir: str,
        size: str = "1024x1536",
    ) -> str:
        image_bytes = await self.backend.generate_scene(
            scene_prompt=prompt.chinese_prompt,
            style_reference=None,
            size=size,
        )

        output_path = Path(output_dir) / "characters" / f"{entity.id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)

        return str(output_path)

    async def generate_item(
        self,
        entity: Entity,
        prompt: Prompt,
        output_dir: str = "",
        size: str = "1024x1024",
    ) -> str:
        """
        生成物品设定图

        Args:
            entity: 物品实体
            prompt: 物品提示词
            output_dir: 输出目录
            size: 输出尺寸，默认 1024x1024（方形物品图）

        Returns:
            str: 生成图路径

        Raises:
            Exception: 生成失败时抛出异常
        """
        image_bytes = await self.backend.generate_item(
            item_prompt=prompt.chinese_prompt,
            size=size,
        )
        
        output_path = Path(output_dir) / "items" / f"{entity.id}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return str(output_path)

    async def generate_all(
        self,
        entities: list[Entity],
        prompts: list[Prompt],
        world_bible: WorldBible,
        face_anchor_dir: str,
        output_dir: str,
    ) -> dict[str, list[str]]:
        """
        批量生成所有图片

        Args:
            entities: 实体列表
            prompts: 提示词列表
            world_bible: 世界观锚定文档（用于获取视觉规则）
            face_anchor_dir: 面部锚定图目录
            output_dir: 输出目录

        Returns:
            dict[str, list[str]]: 
                {
                    "characters": [path, ...], 
                    "scenes": [path, ...], 
                    "items": [path, ...]
                }

        Raises:
            Exception: 批量生成过程中出现错误时抛出异常
        """
        prompt_map = {p.entity_id: p for p in prompts}
        results = {"characters": [], "scenes": [], "items": [], "errors": []}
        first_scene_path = None

        semaphore = asyncio.Semaphore(max(1, self.max_parallel))

        async def generate_entity(entity: Entity) -> tuple[str, str | None]:
            prompt = prompt_map.get(entity.id)
            if not prompt:
                return "skip", None

            try:
                async with semaphore:
                    if entity.type == EntityType.CHARACTER:
                        face_anchor_path = str(Path(face_anchor_dir) / f"{entity.id}.png")
                        if not Path(face_anchor_path).exists():
                            path = await self.generate_character_without_face(
                                entity,
                                prompt,
                                output_dir,
                                self.default_sizes.get("character", "1024x1536")
                            )
                        else:
                            path = await self.generate_character(
                                entity,
                                prompt,
                                face_anchor_path,
                                output_dir,
                                self.default_sizes.get("character", "1024x1536")
                            )
                        return "characters", path

                    if entity.type == EntityType.SCENE:
                        path = await self.generate_scene(
                            entity,
                            prompt,
                            first_scene_path,
                            output_dir,
                            self.default_sizes.get("scene", "1536x1024")
                        )
                        return "scenes", path

                    if entity.type == EntityType.ITEM:
                        path = await self.generate_item(
                            entity,
                            prompt,
                            output_dir,
                            self.default_sizes.get("item", "1024x1024")
                        )
                        return "items", path

            except Exception as e:
                message = f"Generate {entity.type.value} {entity.name} image failed: {e}"
                print(message)
                return "errors", message

            return "skip", None

        task_results = await asyncio.gather(*(generate_entity(entity) for entity in entities))

        for key, value in task_results:
            if key in results and value:
                results[key].append(value)

        return results

    async def generate_character_variation(
        self,
        entity: Entity,
        prompt: Prompt,
        face_anchor_path: str,
        clothing_description: str,
        output_dir: str,
        size: str = "1024x1536",
    ) -> str:
        """
        生成角色变体图（不同服饰/姿态）

        Args:
            entity: 角色实体
            prompt: 基础角色提示词
            face_anchor_path: 面部锚定图路径
            clothing_description: 服饰描述（如"穿着红色长裙"）
            output_dir: 输出目录
            size: 输出尺寸

        Returns:
            str: 生成图路径
        """
        combined_prompt = f"{prompt.chinese_prompt}, {clothing_description}"
        
        face_anchor_bytes = Path(face_anchor_path).read_bytes()
        
        image_bytes = await self.backend.generate_character_with_face(
            character_prompt=combined_prompt,
            face_anchor_bytes=face_anchor_bytes,
            size=size,
        )
        
        output_path = Path(output_dir) / "characters" / f"{entity.id}_variation.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        
        return str(output_path)

    async def regenerate_character(
        self,
        entity: Entity,
        prompt: Prompt,
        face_anchor_path: str,
        output_dir: str,
        size: str = "1024x1536",
    ) -> str:
        """
        重新生成角色全身图（用于一致性验证失败后的重新生成）

        Args:
            entity: 角色实体
            prompt: 角色提示词
            face_anchor_path: 面部锚定图路径
            output_dir: 输出目录
            size: 输出尺寸

        Returns:
            str: 新生成图路径
        """
        output_path = await self.generate_character(
            entity, 
            prompt, 
            face_anchor_path, 
            output_dir,
            size
        )
        return output_path

    def get_output_path(
        self, 
        entity: Entity, 
        output_dir: str, 
        suffix: str = ""
    ) -> Path:
        """
        获取实体的输出路径

        Args:
            entity: 实体
            output_dir: 输出目录
            suffix: 文件名后缀

        Returns:
            Path: 输出文件路径
        """
        type_dir = {
            EntityType.CHARACTER: "characters",
            EntityType.SCENE: "scenes",
            EntityType.ITEM: "items",
            EntityType.CREATURE: "characters",
        }.get(entity.type, "characters")
        
        filename = f"{entity.id}{suffix}.png"
        return Path(output_dir) / type_dir / filename
