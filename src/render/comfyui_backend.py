from typing import Dict, Any, Optional, List
import httpx
import asyncio
import json
import base64
from pathlib import Path


class ComfyUIBackend:
    """ComfyUI 后端"""

    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        """初始化 ComfyUI 后端
        
        Args:
            base_url: ComfyUI 服务器地址
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = 300

    async def _ensure_connected(self) -> bool:
        """确保已连接到 ComfyUI
        
        Returns:
            是否连接成功
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f'{self.base_url}/system_stats')
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def _get_workflows(self) -> List[Dict]:
        """获取可用工作流
        
        Returns:
            工作流列表
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f'{self.base_url}/object_info')
            response.raise_for_status()
            return response.json()

    async def _queue_prompt(self, prompt_data: Dict) -> Dict[str, Any]:
        """将提示放入队列
        
        Args:
            prompt_data: 提示数据
            
        Returns:
            队列结果
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f'{self.base_url}/prompt',
                json={'prompt': prompt_data}
            )
            response.raise_for_status()
            return response.json()

    async def _get_history(self, prompt_id: str) -> Dict:
        """获取执行历史
        
        Args:
            prompt_id: 提示ID
            
        Returns:
            历史记录
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f'{self.base_url}/history/{prompt_id}')
            response.raise_for_status()
            return response.json()

    async def _get_history_with_retry(
        self,
        prompt_id: str,
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> Dict:
        """带重试的历史查询
        
        Args:
            prompt_id: 提示ID
            max_wait: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）
            
        Returns:
            历史记录
        """
        import time
        elapsed = 0
        
        while elapsed < max_wait:
            history = await self._get_history(prompt_id)
            
            if prompt_id in history:
                return history[prompt_id]
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        return {}

    def _build_text_to_image_workflow(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg: float = 7.0,
        sampler: str = "DPM++ 2M Karras",
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """构建文生图工作流
        
        Args:
            prompt: 提示词
            width: 宽度
            height: 高度
            steps: 步数
            cfg: CFG比例
            sampler: 采样器
            seed: 随机种子
            
        Returns:
            工作流字典
        """
        workflow = {
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 0]
                }
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "low quality, bad quality, blurry, distorted",
                    "clip": ["4", 0]
                }
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed if seed is not None else random.randint(0, 0xFFFFFFFF),
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler,
                    "scheduler": "normal",
                    "positive": ["3", 0],
                    "negative": ["5", 0],
                    "model": ["7", 0]
                }
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "model": "default模型"
                }
            }
        }
        
        return workflow

    def generate(
        self,
        prompt: str,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """生成图像
        
        Args:
            prompt: 提示词
            output_dir: 输出目录
            **kwargs: 其他参数
            
        Returns:
            生成结果
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._generate_async(prompt, output_dir, **kwargs)
        )

    async def _generate_async(
        self,
        prompt: str,
        output_dir: str,
        **kwargs
    ) -> Dict[str, Any]:
        """异步生成图像
        
        Args:
            prompt: 提示词
            output_dir: 输出目录
            **kwargs: 其他参数
            
        Returns:
            生成结果
        """
        width = kwargs.get('width', 1024)
        height = kwargs.get('height', 1024)
        steps = kwargs.get('steps', 30)
        cfg = kwargs.get('cfg_scale', 7.0)
        sampler = kwargs.get('sampler', 'DPM++ 2M Karras')
        seed = kwargs.get('seed')
        
        workflow = self._build_text_to_image_workflow(
            prompt, width, height, steps, cfg, sampler, seed
        )
        
        try:
            queue_result = await self._queue_prompt(workflow)
            prompt_id = queue_result.get('prompt_id')
            
            if not prompt_id:
                return {'success': False, 'error': 'Failed to queue prompt'}
            
            history = await self._get_history_with_retry(prompt_id)
            
            if not history:
                return {'success': False, 'error': 'Timeout waiting for generation'}
            
            return {'success': True, 'prompt_id': prompt_id, 'history': history}
            
        except httpx.HTTPError as e:
            return {'success': False, 'error': str(e)}

    async def _upload_image_async(self, image_path: str) -> Optional[str]:
        """异步上传图像
        
        Args:
            image_path: 图像路径
            
        Returns:
            上传后的图像名称
        """
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()
        
        files = {
            'image': (Path(image_path).name, open(image_path, 'rb'), 'image/png')
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f'{self.base_url}/upload/image',
                    files=files
                )
                response.raise_for_status()
                result = response.json()
                return result.get('name')
            except httpx.HTTPError:
                return None

    def edit(
        self,
        image_path: str,
        prompt: str,
        output_dir: str,
        mask_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """编辑图像
        
        Args:
            image_path: 图像路径
            prompt: 提示词
            output_dir: 输出目录
            mask_path: 遮罩路径
            
        Returns:
            编辑结果
        """
        raise NotImplementedError("ComfyUI编辑功能尚未实现")

    async def _edit_async(
        self,
        image_path: str,
        prompt: str,
        output_dir: str,
        mask_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """异步编辑图像
        
        Args:
            image_path: 图像路径
            prompt: 提示词
            output_dir: 输出目录
            mask_path: 遮罩路径
            
        Returns:
            编辑结果
        """
        image_name = await self._upload_image_async(image_path)
        
        if not image_name:
            return {'success': False, 'error': 'Failed to upload image'}
        
        return {'success': True, 'uploaded_name': image_name}


import random
