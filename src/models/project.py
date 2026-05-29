"""
项目的Pydantic数据模型
定义项目配置和状态数据结构
"""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    CREATED = "created"
    WORLD_BIBLE_DONE = "world_bible_done"
    EXTRACTING = "extracting"
    EXTRACT_DONE = "extract_done"
    PROMPTING = "prompting"
    PROMPT_DONE = "prompt_done"
    ILLUSTRATING = "illustrating"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(BaseModel):
    """项目"""
    id: str = ""
    novel_title: str = ""
    input_path: str = ""
    status: ProjectStatus = ProjectStatus.CREATED
    world_bible_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
