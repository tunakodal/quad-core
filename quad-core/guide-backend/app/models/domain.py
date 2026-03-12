"""
Shared Model — Core domain entities used across backend services,
integration components, and the API boundary.

Aligned with GUIDE Low-Level Design Document (Appendix A, §5).
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


# ── Enums ─────────────────────────────────────────────────────────

class Language(str, Enum):
    """Supported language options for content and audio selection."""
    TR = "TR"
    EN = "EN"
    DE = "DE"


class RoutingProfile(str, Enum):
    """Routing mode used by the OSRM engine."""
    DRIVING = "driving"
    WALKING = "walking"


# ── Value Objects ─────────────────────────────────────────────────

class GeoPoint(BaseModel):
    """Represents a geographical coordinate (WGS84)."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class MediaAsset(BaseModel):
    """Represents a media resource reference (image/audio)."""
    asset_id: str
    url_or_path: str
    media_type: str  # "image" | "audio"


# ── Core Domain Entities ──────────────────────────────────────────

class Poi(BaseModel):
    """Represents a Point of Interest (POI) in the dataset."""
    id: str
    name: str
    category: str
    city: str
    location: GeoPoint
    estimated_visit_duration: int  # minutes


class PoiContent(BaseModel):
    """Content package returned for a POI, including text, images, and audio reference."""
    poi_id: str
    language: Language = Language.EN
    description_text: str = ""
    images: list[MediaAsset] = []
    audio: Optional[MediaAsset] = None


class RouteSegment(BaseModel):
    """Represents a portion of the route (typically one day)."""
    day_index: int
    path: list[GeoPoint] = []
    distance: int = 0       # meters
    duration: int = 0       # seconds
    geometry_encoded: str = ""


class DayPlan(BaseModel):
    """Represents a single day's schedule and its associated route segment."""
    day_index: int
    pois: list[Poi] = []
    route_segment: Optional[RouteSegment] = None


class Itinerary(BaseModel):
    """Represents a multi-day structured travel plan."""
    days: list[DayPlan] = []
    total_distance: int = 0   # meters
    total_duration: int = 0   # seconds


class RoutePlan(BaseModel):
    """Structured route output used for map visualization and day-by-day navigation."""
    segments: list[RouteSegment] = []
    total_distance: int = 0
    total_duration: int = 0
    geometry_encoded: str = ""
