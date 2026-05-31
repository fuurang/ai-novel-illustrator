from typing import Dict, Any, Optional, List
import json
import asyncio
from pathlib import Path


class LLMAdapter:
    """LLM适配器，使用litellm调用各种LLM API"""

    def __init__(self, config: Dict[str, Any]):
        """初始化LLM适配器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.llm_config = config.get('llm', {})
        
        self.provider = self.llm_config.get('provider', 'deepseek')
        self.model = self.llm_config.get('model', 'deepseek-chat')
        self.api_key = self.llm_config.get('api_key', '')
        self.base_url = self.llm_config.get('base_url', 'https://api.deepseek.com/v1')
        self.temperature = self.llm_config.get('temperature', 0.3)
        self.max_tokens = self.llm_config.get('max_tokens', 4096)
        
        self._client = None

    def _get_client(self):
        """获取litellm客户端"""
        if self._client is None:
            try:
                import litellm
                litellm.drop_params = True
                litellm.set_verbose = False
                self._client = litellm
            except ImportError:
                raise ImportError("请安装 litellm: pip install litellm")
        
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称（可选）
            temperature: 温度（可选）
            max_tokens: 最大token数（可选）
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        client = self._get_client()
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        model_name = model or self.model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens
        
        response = client.completion(
            model=model_name,
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )
        
        return response['choices'][0]['message']['content']

    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """异步生成文本
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称（可选）
            temperature: 温度（可选）
            max_tokens: 最大token数（可选）
            **kwargs: 其他参数
            
        Returns:
            生成的文本
        """
        client = self._get_client()
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        model_name = model or self.model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens
        
        response = await client.acompletion(
            model=model_name,
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )
        
        return response['choices'][0]['message']['content']

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """生成JSON输出
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称（可选）
            json_schema: JSON Schema（可选）
            **kwargs: 其他参数
            
        Returns:
            解析后的JSON字典
        """
        client = self._get_client()
        
        messages = []
        
        base_system = "你是一个专业的JSON生成器。请始终只输出有效的JSON，不要包含任何其他文字。"
        
        if json_schema:
            schema_str = json.dumps(json_schema, ensure_ascii=False, indent=2)
            system_prompt = f"{base_system}\n\n请严格按照以下JSON Schema生成：\n{schema_str}"
        elif system_prompt:
            system_prompt = f"{base_system}\n\n{system_prompt}"
        else:
            system_prompt = base_system
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        model_name = model or self.model
        
        response = client.completion(
            model=model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )
        
        content = response['choices'][0]['message']['content']
        
        return self._parse_json_response(content)

    async def generate_json_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """异步生成JSON输出
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            model: 模型名称（可选）
            json_schema: JSON Schema（可选）
            **kwargs: 其他参数
            
        Returns:
            解析后的JSON字典
        """
        client = self._get_client()
        
        messages = []
        
        base_system = "你是一个专业的JSON生成器。请始终只输出有效的JSON，不要包含任何其他文字。"
        
        if json_schema:
            schema_str = json.dumps(json_schema, ensure_ascii=False, indent=2)
            system_prompt = f"{base_system}\n\n请严格按照以下JSON Schema生成：\n{schema_str}"
        elif system_prompt:
            system_prompt = f"{base_system}\n\n{system_prompt}"
        else:
            system_prompt = base_system
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        model_name = model or self.model
        
        response = await client.acompletion(
            model=model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )
        
        content = response['choices'][0]['message']['content']
        
        return self._parse_json_response(content)

    async def generate_json_with_raw_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """异步生成 JSON，同时返回模型原始输出，便于调试和人工追问。"""
        client = self._get_client()

        base_system = "你是一个专业的JSON生成器。请始终只输出有效的JSON，不要包含任何其他文字。"

        if json_schema:
            schema_str = json.dumps(json_schema, ensure_ascii=False, indent=2)
            final_system_prompt = f"{base_system}\n\n请严格按照以下JSON Schema生成：\n{schema_str}"
        elif system_prompt:
            final_system_prompt = f"{base_system}\n\n{system_prompt}"
        else:
            final_system_prompt = base_system

        messages = [
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await client.acompletion(
            model=model or self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            base_url=self.base_url,
            **kwargs
        )

        raw_content = response['choices'][0]['message']['content']
        return {
            "raw_output": raw_content,
            "parsed_output": self._parse_json_response(raw_content),
            "system_prompt": final_system_prompt,
            "user_prompt": prompt,
        }

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """解析JSON响应
        
        Args:
            content: 响应内容
            
        Returns:
            解析后的字典
        """
        content = content.strip()
        
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start != -1 and json_end != -1:
                json_str = content[json_start:json_end+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            raise ValueError(f"无法解析JSON响应: {content[:200]}")

    def generate_batch(
        self,
        prompts: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> List[str]:
        """批量生成
        
        Args:
            prompts: 提示列表，每个元素包含 'prompt' 键
            system_prompt: 系统提示
            
        Returns:
            生成结果列表
        """
        results = []
        
        for item in prompts:
            prompt = item.get('prompt', '')
            custom_system = item.get('system', system_prompt)
            
            result = self.generate(prompt, custom_system)
            results.append(result)
        
        return results

    async def generate_batch_async(
        self,
        prompts: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_concurrency: int = 3
    ) -> List[str]:
        """异步批量生成
        
        Args:
            prompts: 提示列表
            system_prompt: 系统提示
            max_concurrency: 最大并发数
            
        Returns:
            生成结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def generate_one(item: Dict[str, str]) -> str:
            async with semaphore:
                prompt = item.get('prompt', '')
                custom_system = item.get('system', system_prompt)
                return await self.generate_async(prompt, custom_system)
        
        tasks = [generate_one(item) for item in prompts]
        results = await asyncio.gather(*tasks)
        
        return list(results)
