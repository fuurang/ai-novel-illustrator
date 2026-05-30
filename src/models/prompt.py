from pydantic import BaseModel, Field
from datetime import datetime


class PromptParameters(BaseModel):
    aspect_ratio: str = "1:1"
    steps: int = 30
    cfg_scale: float = 7.0
    sampler: str = "DPM++ 2M Karras"


class Prompt(BaseModel):
    id: str = ""
    entity_id: str = ""
    type: str = ""
    world_prefix_chinese: str = ""
    face_block_chinese: str = ""
    chinese_prompt: str = ""
    negative_prompt: str = ""
    style_tags: list[str] = []
    parameters: PromptParameters = PromptParameters()
    source_quotes: list[dict] = []
    chapter_number: int | None = None
    variant_label: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
