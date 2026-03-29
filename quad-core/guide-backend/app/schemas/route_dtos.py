"""
Route generation and replanning DTOs — request/response shapes for /api/v1/routes/*.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.enums import Language
from app.models.route import Itinerary, RoutePlan
from app.schemas.common import ApiWarning
from app.schemas.travel import TravelPreferences, TravelConstraints


class DayReorderOperation(BaseModel):
    day_index: int
    ordered_poi_ids: list[str]


class UserEdits(BaseModel):
    removed_poi_ids: list[str] = []
    locked_pois_by_day: dict[int, list[str]] = {}
    reorder_operations: list[DayReorderOperation] = []


class RouteRequest(BaseModel):
    preferences: TravelPreferences
    constraints: TravelConstraints
    language: Language = Language.EN


class RouteResponse(BaseModel):
    itinerary: Itinerary
    route_plan: RoutePlan
    warnings: list[ApiWarning] = []
    effective_trip_days: Optional[int] = None


class ReplanRequest(BaseModel):
    existing_itinerary: Itinerary
    edits: UserEdits
    constraints: TravelConstraints
