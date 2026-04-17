from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.enums import Language
from app.models.poi import Poi
from app.models.route import Itinerary, RoutePlan
from app.schemas.common import ApiWarning
from app.schemas.travel import TravelPreferences, TravelConstraints


class DayReorderOperation(BaseModel):
    """Tek bir güne ait POI sırasını yeniden tanımlayan operasyon."""

    day_index: int
    ordered_poi_ids: list[str]


class UserEdits(BaseModel):
    """
    Kullanıcının mevcut itinerary üzerinde yaptığı düzenlemeleri taşır.

    ordered_poi_ids_by_day: {gün_indeksi: [poi_id, ...]} formatında,
    yalnızca değiştirilen günleri içerir. Belirtilmeyen günler dokunulmaz.
    """

    ordered_poi_ids_by_day: dict[int, list[str]] = {}


class RouteRequest(BaseModel):
    """
    Yeni rota oluşturma isteği.

    preferences: Şehir, gün sayısı, kategori ve mesafe tercihleri.
    constraints: Sistem limitleri (max mekan/gün, max mesafe).
    language:    İçerik dili (varsayılan: İngilizce).
    """

    preferences: TravelPreferences
    constraints: TravelConstraints
    language: Language = Language.EN


class RouteResponse(BaseModel):
    """
    Rota oluşturma veya yeniden planlama sonucu.

    itinerary:        Günlük POI planları.
    route_plan:       OSRM'den gelen yol geometrisi ve mesafe/süre bilgileri.
    warnings:         Kısmi plan, yetersiz POI gibi non-fatal uyarılar.
    effective_trip_days: Gerçekte oluşturulan gün sayısı (istenenin altında olabilir).
    available_pois:   Plana dahil edilmemiş, öneri olarak sunulabilecek mekanlar.
    """

    itinerary: Itinerary
    route_plan: RoutePlan
    warnings: list[ApiWarning] = []
    effective_trip_days: Optional[int] = None
    available_pois: list[Poi] = []


class ReplanRequest(BaseModel):
    """
    Kullanıcı düzenlemesi sonrası yeniden planlama isteği.

    existing_itinerary: Düzenlenmeden önceki mevcut plan (stateless — sunucu state tutmuyor).
    edits:              Hangi günlerde hangi değişiklik yapıldığı.
    constraints:        Güncel sistem limitleri.
    """

    existing_itinerary: Itinerary
    edits: UserEdits
    constraints: TravelConstraints