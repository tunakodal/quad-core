from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from app.models.domain import Language, Itinerary, RoutePlan, Poi, PoiContent


# ── Warnings & Errors ──────────────────────────────────────────────

class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"


class ApiWarning(BaseModel):
    code: str
    severity: Severity = Severity.WARN
    message: str


class ApiErrorResponse(BaseModel):
    error_code: str
    message: str
    details: list[str] = []


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[ApiWarning] = []


# ── Travel preferences & constraints ──────────────────────────────

class TravelPreferences(BaseModel):
    city: str
    trip_days: int = Field(..., ge=1, le=10)
    categories: list[str] = []
    max_distance_per_day: int = Field(..., ge=1000)  # meters


class TravelConstraints(BaseModel):
    max_trip_days: int = 10
    max_pois_per_day: int = 9
    max_daily_distance: int = 100_000  # meters


# ── Route generation ───────────────────────────────────────────────

class RouteRequest(BaseModel):
    preferences: TravelPreferences
    constraints: TravelConstraints
    language: Language = Language.EN


class RouteResponse(BaseModel):
    itinerary: Itinerary
    route_plan: RoutePlan
    warnings: list[ApiWarning] = []
    effective_trip_days: Optional[int] = None


# ── Replanning ─────────────────────────────────────────────────────

class DayReorderOperation(BaseModel):
    day_index: int
    ordered_poi_ids: list[str]


class UserEdits(BaseModel):
    removed_poi_ids: list[str] = []
    locked_pois_by_day: dict[int, list[str]] = {}
    reorder_operations: list[DayReorderOperation] = []


class ReplanRequest(BaseModel):
    existing_itinerary: Itinerary
    edits: UserEdits
    constraints: TravelConstraints


# ── POI queries ────────────────────────────────────────────────────

class PoiQuery(BaseModel):
    city: str
    categories: list[str] = []
    text_query: Optional[str] = None


class PoiQueryResponse(BaseModel):
    pois: list[Poi] = []
    warnings: list[ApiWarning] = []


class PoiContentRequest(BaseModel):
    poi_id: str
    language: Language = Language.EN


class PoiContentResponse(BaseModel):
    content: PoiContent
    warnings: list[ApiWarning] = []


# ── Trip day suggestion ────────────────────────────────────────────

class TripDaySuggestionRequest(BaseModel):
    city: str
    categories: list[str] = []
    max_distance_per_day: Optional[int] = None


class TripDaySuggestionResponse(BaseModel):
    max_recommended_days: int
    poi_count: int
    warnings: list[ApiWarning] = []
