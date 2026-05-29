from typing import Dict, Any, Optional
import httpx
import base64
from pathlib import Path
import asyncio


class ChatGPT2APIBackend:
    """ChatGPT2API 后端"""

    def __init__(self, config: Dict[str, Any]):
        """初始化 ChatGPT2API 后端
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.base_url = config.get('base_url', 'http://localhost:3000/v1')
        self.api_key = config.get('api_key', 'biaooo')
        self.model = config.get('model', 'gpt-image-2')
        self.timeout = config.get('timeout', 120)

    async def _generate_async(
        self,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """异步生成图像
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            生成结果
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                'model': self.model,
                'prompt': prompt,
                'n': kwargs.get('n', 1),
                'size': kwargs.get('size', '1024x1024')
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            try:
                response = await client.post(
                    f'{self.base_url}/images/generations',
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {'error': str(e)}

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
        
        return loop.run_until_complete(self._generate_async(prompt, **kwargs))

    async def _edit_async(
        self,
        image_path: str,
        mask_path: Optional[str],
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """异步编辑图像
        
        Args:
            image_path: 图像路径
            mask_path: 遮罩路径
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            编辑结果
        """
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                'model': self.model,
                'image': image_data,
                'prompt': prompt
            }
            
            if mask_path:
                with open(mask_path, 'rb') as f:
                    mask_data = base64.b64encode(f.read()).decode()
                payload['mask'] = mask_data
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            try:
                response = await client.post(
                    f'{self.base_url}/images/edits',
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                return {'error': str(e)}

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
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._edit_async(image_path, mask_path, prompt))

    def _save_image(self, image_data: str, output_path: str) -> str:
        """保存图像
        
        Args:
            image_data: 图像数据（base64或URL）
            output_path: 输出路径
            
        Returns:
            保存的文件路径
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        return output_path

    async def _download_async(self, url: str, output_path: str) -> str:
        """异步下载图像
        
        Args:
            url: 图像URL
            output_path: 输出路径
            
        Returns:
            保存的文件路径
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path

    def download(self, url: str, output_path: str) -> str:
        """下载图像
        
        Args:
            url: 图像URL
            output_path: 输出路径
            
        Returns:
            保存的文件路径
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._download_async(url, output_path))
