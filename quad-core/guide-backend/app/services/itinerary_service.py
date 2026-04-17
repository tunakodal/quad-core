"""
Itinerary Service - planlayici ile repository arasindaki orkestrasyon katmani.

build_itinerary : Verilen POI listesinden Monte Carlo planlayici araciligiyla
                  en iyi gunluk plani secer.
replan          : Kullanici duzenlemelerini mevcut itinerary'ye uygular;
                  yalnizca degisen gunleri yeniden olusturur.
"""
from app.models.poi import Poi
from app.models.route import Itinerary, DayPlan
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints, TravelPreferences
from app.services.itinerary_planner import MonteCarloItineraryPlanner
from app.repositories.interfaces import AbstractPoiRepository
from app.schemas.common import ApiWarning, Severity


class ItineraryService:
    """
    Seyahat programi olusturma ve yeniden planlama is mantigini yonetir.

    Planlayicidan (MonteCarloItineraryPlanner) bagimsizdır; farkli bir
    planlama stratejisi enjekte edilerek algoritma degistirilebilir.
    """

    def __init__(
        self,
        planner: MonteCarloItineraryPlanner,
        poi_repository: AbstractPoiRepository,
    ):
        self.planner = planner
        self.poi_repository = poi_repository

    async def build_itinerary(
        self, pois: list[Poi], constraints: TravelConstraints, prefs: TravelPreferences
    ) -> tuple[Itinerary, list[ApiWarning]]:
        """
        POI listesinden planlayici araciligiyla en iyi itinerary'yi olusturur.

        Uretilen gun sayisi istenen trip_days'den azsa PARTIAL_ITINERARY uyarisi
        eklenir - bu hata degil, POI havuzunun yetersizligini bildiren bir uyaridir.

        Args:
            pois:        Planlama icin aday mekan listesi.
            constraints: Gunluk max mekan sayisi, max mesafe gibi sistem kisitlari.
            prefs:       Kullanicinin istedigi gun sayisi ve sehir bilgisi.

        Returns:
            (Itinerary, warnings) tuple'i.
        """
        itinerary = self.planner.select_best(pois, constraints, prefs)
        warnings: list[ApiWarning] = []
        if len(itinerary.days) < prefs.trip_days:
            warnings.append(
                ApiWarning(
                    code="PARTIAL_ITINERARY",
                    severity=Severity.WARN,
                    message="Requested trip duration could not be fully satisfied with available POIs.",
                )
            )
        return itinerary, warnings

    async def replan(
        self,
        existing: Itinerary,
        edits: UserEdits,
        constraints: TravelConstraints,
        prefs: TravelPreferences,
    ) -> tuple[Itinerary, list[ApiWarning]]:
        """
        Kullanicinin duzenledigi gunleri mevcut itinerary uzerinde gunceller.

        Yalnizca edits.ordered_poi_ids_by_day'de belirtilen gunler yeniden
        olusturulur; diger gunler degismeden korunur. Yeni eklenen POI'lar
        (existing_map'te bulunmayanlar) repository'den sorgulanir.

        Duplicate POI ID'ler sessizce gormezden gelinir (seen set ile).

        Args:
            existing:    Kullanicinin duzenledigi mevcut itinerary.
            edits:       Degisen gunler ve yeni POI sirasi.
            constraints: Seyahat kisitlari (su an aktif kullanilmiyor, ilerisi icin).
            prefs:       Seyahat tercihleri (su an aktif kullanilmiyor, ilerisi icin).

        Returns:
            (Itinerary, warnings) tuple'i.

        Raises:
            ValueError: Belirtilen POI ID'si ne mevcut itinerary'de ne de DB'de bulunuyorsa.
        """
        warnings: list[ApiWarning] = []

        if not edits.ordered_poi_ids_by_day:
            return existing, warnings

        # Mevcut POI'leri map'le
        existing_map = {
            poi.id: poi
            for day in existing.days
            for poi in day.pois
        }

        new_days: list[DayPlan] = []

        for day in existing.days:
            requested_ids = edits.ordered_poi_ids_by_day.get(day.day_index)

            # Bu gun modified degilse aynen koru
            if requested_ids is None:
                new_days.append(day)
                continue

            # Modified gun - POI'leri sirayla topla
            pois: list[Poi] = []
            seen: set[str] = set()

            for pid in requested_ids:
                if pid in seen:
                    continue
                seen.add(pid)

                poi = existing_map.get(pid)

                # Yeni eklenen POI - DB'den al
                if poi is None:
                    poi = await self.poi_repository.find_by_id(pid)

                if poi is None:
                    raise ValueError(f"POI with id '{pid}' could not be found.")

                pois.append(poi)

            new_days.append(
                DayPlan(day_index=day.day_index, pois=pois)
            )

        return Itinerary(days=new_days), warnings
