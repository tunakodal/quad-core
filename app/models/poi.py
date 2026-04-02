"""
Point of Interest (POI) domain entities.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.enums import Language
from app.models.geo import GeoPoint
from app.models.media import MediaAsset


class Poi(BaseModel):
    """Represents a Point of Interest in the dataset."""
    id: str
    name: str
    category: str
    city: str
    location: GeoPoint
    estimated_visit_duration: int  # minutes


class PoiContent(BaseModel):
    """Content package for a POI: text description, images, and optional audio."""
    poi_id: str
    language: Language = Language.EN
    description_text: str = ""
    images: list[MediaAsset] = []
    audio: Optional[MediaAsset] = None
