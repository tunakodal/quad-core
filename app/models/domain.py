from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class Language(str, Enum):
    TR = "TR"
    EN = "EN"
    DE = "DE"


class RoutingProfile(str, Enum):
    DRIVING = "driving"
    WALKING = "walking"


class GeoPoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class MediaAsset(BaseModel):
    asset_id: str
    url_or_path: str
    media_type: str  # "image" | "audio"


class Poi(BaseModel):
    id: str
    name: str
    category: str
    location: GeoPoint
    estimated_visit_duration: int  # minutes


class PoiContent(BaseModel):
    poi_id: str
    language: Language
    description_text: str = ""
    images: list[MediaAsset] = []
    audio: Optional[MediaAsset] = None


class RouteSegment(BaseModel):
    day_index: int
    distance: int       # meters
    duration: int       # seconds
    geometry_encoded: str = ""


class DayPlan(BaseModel):
    day_index: int
    pois: list[Poi] = []
    route_segment: Optional[RouteSegment] = None


class Itinerary(BaseModel):
    days: list[DayPlan] = []
    total_distance: int = 0   # meters
    total_duration: int = 0   # seconds


class RoutePlan(BaseModel):
    segments: list[RouteSegment] = []
    total_distance: int = 0
    total_duration: int = 0
    geometry_encoded: str = ""
