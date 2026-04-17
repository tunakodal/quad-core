"""
Trip day suggestion DTOs — request/response shapes for /api/v1/routes/suggest-days.
"""
from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ApiWarning


class TripDaySuggestionRequest(BaseModel):
    """Maksimum onerilecek gezi suresi icin istek govdesi."""
    city: str
    categories: list[str] = []
    max_distance_per_day: Optional[int] = None


class TripDaySuggestionResponse(BaseModel):
    """Gezi suresi onerisi endpoint'inden donen yanit."""
    max_recommended_days: int
    poi_count: int
    warnings: list[ApiWarning] = []
