"""
图片生成Web集成模块
为Web UI提供统一的图片生成接口
整合面部锚定、角色图、场景图、物品图的生成功能
"""

import asyncio
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from src.render.chatgpt2api_backend import ChatGPT2APIBackend
from src.core.face_anchor import FaceAnchorGenerator
from src.core.image_generator import ImageGenerator
from src.models.entity import Entity, EntityType
from src.models.prompt import Prompt
from src.models.world_bible import WorldBible


class WebImageGenerator:
    """
    图片生成的Web集成类
    
    提供统一的异步图片生成接口，支持：
    - 面部锚定图生成
    - 角色全身图生成（基于面部锚定）
    - 场景背景图生成
    - 物品设定图生成
    - 批量生成所有图片
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化图片生成器
        
        Args:
            config: 配置字典，包含：
                - chatgpt2api: ChatGPT2API后端配置
                - face_anchor: 面部锚定生成器配置
                - image_generator: 图片生成器配置
        """
        self.config = config or {}
        
        # 初始化ChatGPT2API后端
        chatgpt2api_config = self.config.get("chatgpt2api", {})
        self.backend = ChatGPT2APIBackend(chatgpt2api_config)
        
        # 初始化面部锚定生成器（需要LLM和提示词加载器）
        self.face_anchor_gen = None
        
        # 初始化图片生成器
        image_gen_config = self.config.get("image_generator", {})
        self.image_gen = ImageGenerator(self.backend, image_gen_config)
        
        # 进度回调
        self.progress_callback: Optional[Callable] = None
        
        # 默认尺寸配置
        self.default_sizes = {
            "character": "1024x1536",
            "scene": "1536x1024",
            "item": "1024x1024",
            "face_anchor": "1024x1024",
        }
    
    def is_available(self) -> bool:
        """
        检查生图后端是否可用
        
        Returns:
            bool: 后端是否可用
        """
        return self.backend is not None
    
    async def generate_face_anchor(
        self,
        entity: Entity,
        prompt: Prompt,
        world_bible: WorldBible,
        output_dir: str,
    ) -> Optional[str]:
        """
        生成面部锚定图
        
        面部锚定图是角色的正面面部特写，用于后续保持面部一致性
        
        Args:
            entity: 角色实体
            prompt: 角色提示词
            world_bible: 世界观锚定文档
            output_dir: 输出目录
            
        Returns:
            str: 图片路径，失败返回None
        """
        if not self.is_available():
            print("错误：生图后端不可用")
            return None
        
        try:
            # 生成面部提示词
            face_prompt = prompt.english_prompt
            
            # 如果有面部锚定生成器，使用它来生成更好的提示词
            if self.face_anchor_gen:
                face_prompt = self.face_anchor_gen._generate_face_prompt(
                    entity, prompt, world_bible
                )
            
            # 调用后端生成面部锚定图
            image_bytes = await self.backend._generate_async(
                face_prompt,
                n=1,
                size=self.default_sizes.get("face_anchor", "1024x1024")
            )
            
            # 检查返回结果
            if isinstance(image_bytes, dict) and 'error' in image_bytes:
                print(f"生成面部锚定图API错误: {image_bytes['error']}")
                return None
            
            # 保存图片
            output_path = Path(output_dir) / "face_anchors" / f"{entity.id}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理返回结果（可能是base64或URL）
            if isinstance(image_bytes, dict) and 'data' in image_bytes:
                # 从返回数据中提取图片
                image_data = image_bytes['data'][0].get('url', '')
                if image_data:
                    await self.backend._download_async(image_data, str(output_path))
                else:
                    # 可能是base64格式
                    b64_data = image_bytes['data'][0].get('b64_json', '')
                    if b64_data:
                        import base64
                        output_path.write_bytes(base64.b64decode(b64_data))
                    else:
                        return None
            elif isinstance(image_bytes, bytes):
                output_path.write_bytes(image_bytes)
            
            return str(output_path)
            
        except Exception as e:
            print(f"生成面部锚定图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_character(
        self,
        entity: Entity,
        prompt: Prompt,
        face_anchor_path: str,
        output_dir: str,
    ) -> Optional[str]:
        """
        基于面部锚定图生成角色全身图
        
        使用ChatGPT2API的图片编辑功能，将面部锚定图作为参考，
        生成包含该面部的全身角色图
        
        Args:
            entity: 角色实体
            prompt: 角色提示词
            face_anchor_path: 面部锚定图路径
            output_dir: 输出目录
            
        Returns:
            str: 图片路径
        """
        if not self.is_available():
            print("错误：生图后端不可用")
            return None
        
        try:
            # 检查面部锚定图是否存在
            if not Path(face_anchor_path).exists():
                print(f"错误：面部锚定图不存在: {face_anchor_path}")
                return None
            
            # 读取面部锚定图
            face_bytes = Path(face_anchor_path).read_bytes()
            
            # 使用后端的编辑功能生成角色图
            # 注意：这里需要后端支持face_anchor功能
            result = await self.backend._edit_async(
                image_path=face_anchor_path,
                mask_path=None,
                prompt=prompt.english_prompt
            )
            
            if isinstance(result, dict) and 'error' in result:
                print(f"生成角色图API错误: {result['error']}")
                return None
            
            # 保存图片
            output_path = Path(output_dir) / "characters" / f"{entity.id}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理返回结果
            if isinstance(result, dict) and 'data' in result:
                image_data = result['data'][0].get('url', '')
                if image_data:
                    await self.backend._download_async(image_data, str(output_path))
                else:
                    b64_data = result['data'][0].get('b64_json', '')
                    if b64_data:
                        import base64
                        output_path.write_bytes(base64.b64decode(b64_data))
                    else:
                        return None
            elif isinstance(result, bytes):
                output_path.write_bytes(result)
            
            return str(output_path)
            
        except Exception as e:
            print(f"生成角色图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_scene(
        self,
        entity: Entity,
        prompt: Prompt,
        output_dir: str,
    ) -> Optional[str]:
        """
        生成场景背景图
        
        Args:
            entity: 场景实体
            prompt: 场景提示词
            output_dir: 输出目录
            
        Returns:
            str: 图片路径
        """
        if not self.is_available():
            print("错误：生图后端不可用")
            return None
        
        try:
            # 直接生成场景图
            result = await self.backend._generate_async(
                prompt.english_prompt,
                n=1,
                size=self.default_sizes.get("scene", "1536x1024")
            )
            
            if isinstance(result, dict) and 'error' in result:
                print(f"生成场景图API错误: {result['error']}")
                return None
            
            # 保存图片
            output_path = Path(output_dir) / "scenes" / f"{entity.id}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理返回结果
            if isinstance(result, dict) and 'data' in result:
                image_data = result['data'][0].get('url', '')
                if image_data:
                    await self.backend._download_async(image_data, str(output_path))
                else:
                    b64_data = result['data'][0].get('b64_json', '')
                    if b64_data:
                        import base64
                        output_path.write_bytes(base64.b64decode(b64_data))
                    else:
                        return None
            elif isinstance(result, bytes):
                output_path.write_bytes(result)
            
            return str(output_path)
            
        except Exception as e:
            print(f"生成场景图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_item(
        self,
        entity: Entity,
        prompt: Prompt,
        output_dir: str,
    ) -> Optional[str]:
        """
        生成物品设定图
        
        Args:
            entity: 物品实体
            prompt: 物品提示词
            output_dir: 输出目录
            
        Returns:
            str: 图片路径
        """
        if not self.is_available():
            print("错误：生图后端不可用")
            return None
        
        try:
            # 直接生成物品图
            result = await self.backend._generate_async(
                prompt.english_prompt,
                n=1,
                size=self.default_sizes.get("item", "1024x1024")
            )
            
            if isinstance(result, dict) and 'error' in result:
                print(f"生成物品图API错误: {result['error']}")
                return None
            
            # 保存图片
            output_path = Path(output_dir) / "items" / f"{entity.id}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 处理返回结果
            if isinstance(result, dict) and 'data' in result:
                image_data = result['data'][0].get('url', '')
                if image_data:
                    await self.backend._download_async(image_data, str(output_path))
                else:
                    b64_data = result['data'][0].get('b64_json', '')
                    if b64_data:
                        import base64
                        output_path.write_bytes(base64.b64decode(b64_data))
                    else:
                        return None
            elif isinstance(result, bytes):
                output_path.write_bytes(result)
            
            return str(output_path)
            
        except Exception as e:
            print(f"生成物品图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_all(
        self,
        entities: list[Entity],
        prompts: list[Prompt],
        world_bible: WorldBible,
        output_dir: str,
        progress_callback: Optional[Callable] = None,
    ):
        """
        批量生成所有图片
        
        生成流程：
        1. 先为每个角色生成面部锚定图
        2. 再基于面部锚定图生成角色全身图
        3. 最后生成场景和物品图
        
        使用异步生成器逐个产出结果
        
        Args:
            entities: 实体列表
            prompts: 提示词列表
            world_bible: 世界观锚定文档
            output_dir: 输出目录
            progress_callback: 进度回调函数，签名：callback(name, progress, status)
            
        Yields:
            dict: 生成结果
        """
        if not self.is_available():
            yield {"error": "生图后端不可用，请检查ChatGPT2API服务"}
            return
        
        # 构建提示词映射
        prompt_map = {p.entity_id: p for p in prompts}
        
        # 初始化结果
        results = {
            "characters": [],
            "scenes": [],
            "items": [],
            "face_anchors": [],
            "errors": []
        }
        
        # 统计需要处理的实体数量
        total = len(entities)
        if total == 0:
            yield {"error": "没有需要处理的实体"}
            return
        
        # 第一阶段：生成所有面部锚定图
        face_anchor_paths = {}
        
        if progress_callback:
            progress_callback("初始化", 0.0, "开始生成面部锚定图...")
        
        for i, entity in enumerate(entities):
            if entity.type != EntityType.CHARACTER:
                continue
            
            prompt_obj = prompt_map.get(entity.id)
            if not prompt_obj:
                results["errors"].append(f"{entity.name}: 缺少提示词")
                continue
            
            # 更新进度
            progress = (i + 1) / total
            if progress_callback:
                progress_callback(entity.name, progress * 0.3, f"正在生成 {entity.name} 的面部锚定图...")
            
            # 生成面部锚定图
            face_path = await self.generate_face_anchor(
                entity, prompt_obj, world_bible, output_dir
            )
            
            if face_path:
                face_anchor_paths[entity.id] = face_path
                results["face_anchors"].append(face_path)
            else:
                results["errors"].append(f"{entity.name}: 面部锚定图生成失败")
        
        # 第二阶段：基于面部锚定图生成角色全身图
        if progress_callback:
            progress_callback("生成角色图", 0.3, "开始生成角色全身图...")
        
        char_count = sum(1 for e in entities if e.type == EntityType.CHARACTER)
        char_done = 0
        
        for i, entity in enumerate(entities):
            if entity.type != EntityType.CHARACTER:
                continue
            
            prompt_obj = prompt_map.get(entity.id)
            if not prompt_obj:
                continue
            
            # 更新进度
            char_done += 1
            progress = 0.3 + (char_done / char_count) * 0.4
            if progress_callback:
                progress_callback(entity.name, progress, f"正在生成 {entity.name} 的角色全身图...")
            
            # 获取面部锚定图路径
            face_path = face_anchor_paths.get(entity.id)
            if not face_path:
                results["errors"].append(f"{entity.name}: 缺少面部锚定图，跳过")
                continue
            
            # 生成角色全身图
            char_path = await self.generate_character(
                entity, prompt_obj, face_path, output_dir
            )
            
            if char_path:
                results["characters"].append(char_path)
            else:
                results["errors"].append(f"{entity.name}: 角色全身图生成失败")
        
        # 第三阶段：生成场景和物品图
        if progress_callback:
            progress_callback("生成场景和物品", 0.7, "开始生成场景和物品图...")
        
        scene_item_count = sum(1 for e in entities if e.type in [EntityType.SCENE, EntityType.ITEM])
        scene_item_done = 0
        
        for i, entity in enumerate(entities):
            if entity.type not in [EntityType.SCENE, EntityType.ITEM]:
                continue
            
            prompt_obj = prompt_map.get(entity.id)
            if not prompt_obj:
                results["errors"].append(f"{entity.name}: 缺少提示词")
                continue
            
            # 更新进度
            scene_item_done += 1
            progress = 0.7 + (scene_item_done / scene_item_count) * 0.3
            if progress_callback:
                progress_callback(entity.name, progress, f"正在生成 {entity.name} 的{entity.type.value}图...")
            
            # 生成对应的图片
            if entity.type == EntityType.SCENE:
                path = await self.generate_scene(entity, prompt_obj, output_dir)
                if path:
                    results["scenes"].append(path)
                else:
                    results["errors"].append(f"{entity.name}: 场景图生成失败")
            
            elif entity.type == EntityType.ITEM:
                path = await self.generate_item(entity, prompt_obj, output_dir)
                if path:
                    results["items"].append(path)
                else:
                    results["errors"].append(f"{entity.name}: 物品图生成失败")
        
        # 最终进度
        if progress_callback:
            progress_callback("完成", 1.0, "所有图片生成完成")
        
        # 返回最终结果
        yield results
    
    async def regenerate_single(
        self,
        entity: Entity,
        prompt: Prompt,
        face_anchor_path: Optional[str],
        output_dir: str,
        entity_type: str = None,
    ) -> Optional[str]:
        """
        重新生成单个实体的图片
        
        Args:
            entity: 实体
            prompt: 提示词
            face_anchor_path: 面部锚定图路径（角色需要）
            output_dir: 输出目录
            entity_type: 实体类型，如果为None则使用entity.type
            
        Returns:
            str: 新生成的图片路径
        """
        entity_type = entity_type or entity.type.value
        
        if entity_type == "character":
            if not face_anchor_path:
                print("错误：角色生成需要面部锚定图")
                return None
            return await self.generate_character(entity, prompt, face_anchor_path, output_dir)
        elif entity_type == "scene":
            return await self.generate_scene(entity, prompt, output_dir)
        elif entity_type == "item":
            return await self.generate_item(entity, prompt, output_dir)
        else:
            print(f"错误：不支持的实体类型: {entity_type}")
            return None
    
    def get_generated_images(
        self,
        entity_id: str,
        output_dir: str,
        entity_type: str = None,
    ) -> Dict[str, str]:
        """
        获取实体已生成的图片路径
        
        Args:
            entity_id: 实体ID
            output_dir: 输出目录
            entity_type: 实体类型
            
        Returns:
            dict: 包含各类图片路径的字典
        """
        paths = {}
        
        # 面部锚定图
        face_path = Path(output_dir) / "face_anchors" / f"{entity_id}.png"
        if face_path.exists():
            paths["face_anchor"] = str(face_path)
        
        # 根据类型确定目录
        if entity_type == "character":
            char_path = Path(output_dir) / "characters" / f"{entity_id}.png"
            if char_path.exists():
                paths["character"] = str(char_path)
        elif entity_type == "scene":
            scene_path = Path(output_dir) / "scenes" / f"{entity_id}.png"
            if scene_path.exists():
                paths["scene"] = str(scene_path)
        elif entity_type == "item":
            item_path = Path(output_dir) / "items" / f"{entity_id}.png"
            if item_path.exists():
                paths["item"] = str(item_path)
        
        return paths
