"""
Route and itinerary domain entities — day plans, segments, and full trip structure.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.geo import GeoPoint
from app.models.poi import Poi


class RouteSegment(BaseModel):
    """Represents a single day's portion of the route (OSRM output)."""
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
    """Multi-day structured travel plan."""
    days: list[DayPlan] = []
    total_distance: int = 0   # meters
    total_duration: int = 0   # seconds


class RoutePlan(BaseModel):
    """Structured route output used for map visualization and day-by-day navigation."""
    segments: list[RouteSegment] = []
    total_distance: int = 0
    total_duration: int = 0
    geometry_encoded: str = ""
