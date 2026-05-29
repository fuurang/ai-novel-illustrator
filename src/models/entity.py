from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    CHARACTER = "character"
    SCENE = "scene"
    ITEM = "item"
    CREATURE = "creature"


class SourceQuote(BaseModel):
    chapter: int = 0
    text: str = ""
    location: str = ""


class WorldBinding(BaseModel):
    genre: str = ""
    era: str = ""
    face_style: str = ""
    clothing_system: str = ""
    art_style: str = ""


class Appearance(BaseModel):
    face: str = ""
    hair: str = ""
    body: str = ""
    distinguishing_features: str = ""


class ClothingVariation(BaseModel):
    context: str = ""
    description: str = ""


class Clothing(BaseModel):
    default: str = ""
    variations: list[ClothingVariation] = []


class Relationship(BaseModel):
    target: str = ""
    relation: str = ""
    name: str = ""


class CharacterAttributes(BaseModel):
    gender: str = ""
    age_range: str = ""
    appearance: Appearance = Appearance()
    clothing: Clothing = Clothing()
    personality: str = ""
    abilities: list[str] = []
    relationships: list[Relationship] = []


class SceneAttributes(BaseModel):
    environment_type: str = ""
    time_of_day: str = ""
    weather: str = ""
    visual_description: str = ""
    atmosphere: str = ""
    key_landmarks: list[str] = []
    color_palette: str = ""


class ItemAttributes(BaseModel):
    category: str = ""
    visual_description: str = ""
    material: str = ""
    size: str = ""
    special_effects: str = ""
    owner: str = ""


class Entity(BaseModel):
    id: str = ""
    project_id: str = ""
    name: str = ""
    aliases: list[str] = []
    type: EntityType = EntityType.CHARACTER
    world_binding: WorldBinding = WorldBinding()
    attributes: dict = {}
    source_quotes: list[SourceQuote] = []
    first_appearance_chapter: int | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
