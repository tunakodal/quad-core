from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.enums import Language
from app.models.poi import Poi
from app.models.route import Itinerary, RoutePlan
from app.schemas.common import ApiWarning
from app.schemas.travel import TravelPreferences, TravelConstraints


class DayReorderOperation(BaseModel):
    """Bir gundeki POI'lerin yeniden siralanma operasyonunu temsil eder."""
    day_index: int
    ordered_poi_ids: list[str]


class UserEdits(BaseModel):
    """Kullanicinin mevcut rotaya uygulayacagi duzenlemeleri icerir."""
    ordered_poi_ids_by_day: dict[int, list[str]] = {}


class RouteRequest(BaseModel):
    """Rota olusturma endpoint'ine gonderilen istek govdesi."""
    preferences: TravelPreferences
    constraints: TravelConstraints
    language: Language = Language.EN


class RouteResponse(BaseModel):
    """Rota olusturma endpoint'inden donen yanit: gunluk plan, rota ve uyarilar."""
    itinerary: Itinerary
    route_plan: RoutePlan
    warnings: list[ApiWarning] = []
    effective_trip_days: Optional[int] = None
    available_pois: list[Poi] = []


class ReplanRequest(BaseModel):
    """Mevcut bir rotayi kullanici duzenlemeleriyle yeniden planlamak icin istek govdesi."""
    existing_itinerary: Itinerary
    edits: UserEdits
    constraints: TravelConstraints