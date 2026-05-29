"""
提示词的Pydantic数据模型
定义图片生成提示词数据结构
"""

from pydantic import BaseModel, Field
from datetime import datetime


class PromptParameters(BaseModel):
    """提示词参数"""
    aspect_ratio: str = "1:1"
    steps: int = 30
    cfg_scale: float = 7.0
    sampler: str = "DPM++ 2M Karras"


class Prompt(BaseModel):
    """图片生成提示词"""
    id: str = ""
    entity_id: str = ""
    type: str = ""
    world_prefix_chinese: str = ""
    world_prefix_english: str = ""
    face_block_chinese: str = ""
    face_block_english: str = ""
    chinese_prompt: str = ""
    english_prompt: str = ""
    negative_prompt: str = ""
    style_tags: list[str] = []
    parameters: PromptParameters = PromptParameters()
    source_quotes: list[dict] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
