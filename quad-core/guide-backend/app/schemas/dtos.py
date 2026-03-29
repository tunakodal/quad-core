"""
Backward-compatible re-export module.

All DTOs have been moved to focused submodules:
  - app.schemas.common          → Severity, ApiWarning, ApiErrorResponse, ValidationResult
  - app.schemas.travel          → TravelPreferences, TravelConstraints
  - app.schemas.route_dtos      → RouteRequest, RouteResponse, ReplanRequest,
                                   UserEdits, DayReorderOperation
  - app.schemas.poi_dtos        → PoiQuery, PoiQueryResponse,
                                   PoiContentRequest, PoiContentResponse
  - app.schemas.suggestion_dtos → TripDaySuggestionRequest, TripDaySuggestionResponse

New code should import directly from those submodules.
This file exists only to avoid breaking existing imports (e.g. tests).
"""
from app.schemas.common import Severity, ApiWarning, ApiErrorResponse, ValidationResult
from app.schemas.travel import TravelPreferences, TravelConstraints
from app.schemas.route_dtos import (
    DayReorderOperation, UserEdits,
    RouteRequest, RouteResponse, ReplanRequest,
)
from app.schemas.poi_dtos import (
    PoiQuery, PoiQueryResponse,
    PoiContentRequest, PoiContentResponse,
)
from app.schemas.suggestion_dtos import TripDaySuggestionRequest, TripDaySuggestionResponse

__all__ = [
    "Severity", "ApiWarning", "ApiErrorResponse", "ValidationResult",
    "TravelPreferences", "TravelConstraints",
    "DayReorderOperation", "UserEdits", "RouteRequest", "RouteResponse", "ReplanRequest",
    "PoiQuery", "PoiQueryResponse", "PoiContentRequest", "PoiContentResponse",
    "TripDaySuggestionRequest", "TripDaySuggestionResponse",
]
