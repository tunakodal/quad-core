from __future__ import annotations
from typing import Optional

from pydantic import BaseModel

from app.models.enums import Language
from app.models.poi import Poi
from app.models.route import Itinerary, RoutePlan
from app.schemas.common import ApiWarning
from app.schemas.travel import TravelPreferences, TravelConstraints


class DayReorderOperation(BaseModel):
    """Tek bir gune ait POI sirasini yeniden tanimlayan operasyon."""

    day_index: int
    ordered_poi_ids: list[str]


class UserEdits(BaseModel):
    """
    Kullanicinin mevcut itinerary uzerinde yaptigi duzenlemeleri tasir.

    ordered_poi_ids_by_day: {gun_indeksi: [poi_id, ...]} formatinda,
    yalnizca degistirilen gunleri icerir. Belirtilmeyen gunler dokunulmaz.
    """

    ordered_poi_ids_by_day: dict[int, list[str]] = {}


class RouteRequest(BaseModel):
    """
    Yeni rota olusturma istegi.

    preferences: Sehir, gun sayisi, kategori ve mesafe tercihleri.
    constraints: Sistem limitleri (max mekan/gun, max mesafe).
    language:    Icerik dili (varsayilan: Ingilizce).
    """

    preferences: TravelPreferences
    constraints: TravelConstraints
    language: Language = Language.EN


class RouteResponse(BaseModel):
    """
    Rota olusturma veya yeniden planlama sonucu.

    itinerary:          Gunluk POI planlari.
    route_plan:         OSRM'den gelen yol geometrisi ve mesafe/sure bilgileri.
    warnings:           Kismi plan, yetersiz POI gibi non-fatal uyarilar.
    effective_trip_days: Gercekte olusturulan gun sayisi (istenenin altinda olabilir).
    available_pois:     Plana dahil edilmemis, oneri olarak sunulabilecek mekanlar.
    """

    itinerary: Itinerary
    route_plan: RoutePlan
    warnings: list[ApiWarning] = []
    effective_trip_days: Optional[int] = None
    available_pois: list[Poi] = []


class ReplanRequest(BaseModel):
    """
    Kullanici duzenlemesi sonrasi yeniden planlama istegi.

    existing_itinerary: Duzenlenmeden onceki mevcut plan (stateless -- sunucu state tutmuyor).
    edits:              Hangi gunlerde hangi degisiklik yapildi.
    constraints:        Guncel sistem limitleri.
    """

    existing_itinerary: Itinerary
    edits: UserEdits
    constraints: TravelConstraints
