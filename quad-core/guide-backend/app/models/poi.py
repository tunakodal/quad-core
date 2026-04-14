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

    # existing simple category field for UI/filter compatibility
    category: str

    # richer taxonomy fields
    main_category_1: str | None = None
    main_category_2: str | None = None
    sub_category_1: str | None = None
    sub_category_2: str | None = None
    sub_category_3: str | None = None
    sub_category_4: str | None = None

    city: str
    location: GeoPoint
    estimated_visit_duration: int  # minutes

    google_rating: float | None = None
    google_reviews_total: int | None = None


class PoiContent(BaseModel):
    """Content package for a POI: text description, images, and optional audio."""
    poi_id: str
    language: Language = Language.EN
    description_text: str = ""
    images: list[MediaAsset] = []
    audio: Optional[MediaAsset] = None

class RandomPoiItem(BaseModel):
    id: str
    name: str
    city: str

    main_category_1: str | None = None
    main_category_2: str | None = None
    sub_category_1: str | None = None
    sub_category_2: str | None = None
    sub_category_3: str | None = None
    sub_category_4: str | None = None

    lat: float
    lng: float

    google_rating: float | None = None
    google_reviews_total: int | None = None


class RandomPoiResponse(BaseModel):
    items: list[RandomPoiItem]