from pydantic import BaseModel, Field
from datetime import datetime


class Chapter(BaseModel):
    id: str = ""
    project_id: str = ""
    number: int = 0
    title: str = ""
    text: str = ""
    is_processed: bool = False
    entity_ids: list[str] = []
    image_ids: list[str] = []
    summary: str = ""
