"""
Routing Service - OSRM entegrasyonu uzerinden rota hesaplama ve guncelleme.

RouteAssembler: OSRM ciktilarini RoutePlan modeline donusturur.
RoutingService: Her gun icin OSRM'e waypoint gonderir, sonuclari Itinerary'ye yazar.
"""
from app.models.enums import RoutingProfile
from app.models.route import Itinerary, RoutePlan, RouteSegment
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints
from app.integration.osrm_client import OsrmClient, OsrmRouteResponse
from app.schemas.common import ApiWarning


class RouteAssembler:
    """
    OSRM ciktilarini (mesafe, sure, encoded geometri) gunluk RouteSegment'lere
    donusturur ve bunlari tek bir RoutePlan altinda toplar.

    RoutingService ile ayri tutulmasinin nedeni: OSRM'den bagimsiz olarak
    farkli kaynaklardan gelen rota verilerinin de ayni RoutePlan modeline
    kolayca aktarilabilmesi.
    """

    def assemble(self, itinerary: Itinerary, osrm_outputs) -> RoutePlan:
        """
        Her gun icin OSRM ciktisini RouteSegment'e cevirir ve toplamlari hesaplar.

        Args:
            itinerary:    Gun planlarini iceren seyahat programi.
            osrm_outputs: Her gune karsilik gelen OsrmRouteResponse listesi
                          (itinerary.days ile ayni sirada olmali).

        Returns:
            Tum gunleri kapsayan RoutePlan. combined_geometry olarak son gunun
            geometrisi saklanir (harita render icin yeterlidir).
        """
        segments: list[RouteSegment] = []
        total_distance = 0
        total_duration = 0
        combined_geometry = ""

        for day, osrm in zip(itinerary.days, osrm_outputs):
            seg = RouteSegment(
                day_index=day.day_index,
                distance=osrm.distance,
                duration=osrm.duration,
                geometry_encoded=osrm.geometry_encoded,
            )
            segments.append(seg)
            total_distance += osrm.distance
            total_duration += osrm.duration
            combined_geometry = osrm.geometry_encoded

        return RoutePlan(
            segments=segments,
            total_distance=total_distance,
            total_duration=total_duration,
            geometry_encoded=combined_geometry,
        )


class RoutingService:
    """
    Itinerary'deki her gun icin OSRM uzerinden gercek yol rotasi hesaplar.

    generate_route           : Yeni olusturulmus bir itinerary icin tum gunlerin
                               rotasini hesaplar. OSRM'in donurdugu en uygun
                               waypoint sirasi ile POI listesini gunceller.
    update_route_after_edits : Kullanici duzenlemesi sonrasi sadece degisen
                               gunleri yeniden hesaplar; digerlerinin mevcut
                               segmentleri korunur (gereksiz OSRM cagrisindan kacinilir).
    """

    def __init__(self, osrm_client: OsrmClient, route_assembler: RouteAssembler):
        self.osrm_client = osrm_client
        self.route_assembler = route_assembler

    async def generate_route(
        self, itinerary: Itinerary, constraints: TravelConstraints
    ) -> tuple[RoutePlan, list[ApiWarning]]:
        """
        Tum gunler icin OSRM trip API'sini cagirip RoutePlan olusturur.

        OSRM'in trip endpoint'i waypoint sirasini optimize eder (TSP).
        Donen waypoint_order ile itinerary'deki POI sirasi guncellenir;
        boylece frontend ile backend sirasi tutarli kalir.

        Args:
            itinerary:   Gun planlarini iceren seyahat programi.
            constraints: Gunluk maksimum mesafe gibi seyahat kisitlari.

        Returns:
            (RoutePlan, warnings) tuple'i. Mevcut implementasyonda warnings
            her zaman bos doner; ileride asim uyarilari eklenebilir.

        Raises:
            httpx.HTTPError: OSRM servisine ulasilamazsa (ust katmanda 503'e map'lenir).
        """
        osrm_outputs = []

        for day in itinerary.days:
            if not day.pois:
                continue
            waypoints = [poi.location for poi in day.pois]
            osrm_result = await self.osrm_client.trip(
                waypoints, RoutingProfile.DRIVING
            )

            order = osrm_result.waypoint_order
            day.pois = [day.pois[i] for i in order]

            osrm_outputs.append(osrm_result)

        route_plan = self.route_assembler.assemble(itinerary, osrm_outputs)

        for day, seg in zip(itinerary.days, route_plan.segments):
            day.route_segment = seg

        warnings: list[ApiWarning] = []
        return route_plan, warnings

    async def update_route_after_edits(
        self, itinerary: Itinerary, edits: UserEdits
    ) -> tuple[RoutePlan, list[ApiWarning]]:
        """
        Kullanici duzenlemesi sonrasi yalnizca degisen gunlerin rotasini yeniden hesaplar.

        Degisen gunlerde OSRM route endpoint'i cagrilir (trip degil - kullanicinin
        belirledigi sira korunur, optimize edilmez). Degismemis gunlerde mevcut
        route_segment kullanilir; segment yoksa yeniden hesaplanir.

        Args:
            itinerary: Duzenlemeler uygulanmis guncel itinerary.
            edits:     Hangi gunlerin hangi POI sirasiyla degistigini belirten duzenlemeler.

        Returns:
            (RoutePlan, warnings) tuple'i.

        Raises:
            httpx.HTTPError: OSRM servisine ulasilamazsa (ust katmanda 503'e map'lenir).
        """
        warnings: list[ApiWarning] = []
        affected_days = set(edits.ordered_poi_ids_by_day.keys())

        osrm_outputs = []

        for day in itinerary.days:
            if day.day_index in affected_days:
                # Modified gun - frontend sirasiyla route al
                waypoints = [poi.location for poi in day.pois]
                if waypoints:
                    result = await self.osrm_client.route(
                        waypoints, RoutingProfile.DRIVING
                    )
                    osrm_outputs.append(result)
                else:
                    osrm_outputs.append(OsrmRouteResponse(
                        distance=0, duration=0,
                        geometry_encoded="", waypoint_order=[],
                    ))
            else:
                # Degismemis gun - mevcut segment'i koru
                if day.route_segment:
                    osrm_outputs.append(OsrmRouteResponse(
                        distance=day.route_segment.distance,
                        duration=day.route_segment.duration,
                        geometry_encoded=day.route_segment.geometry_encoded,
                        waypoint_order=list(range(len(day.pois))),
                    ))
                else:
                    waypoints = [poi.location for poi in day.pois]
                    if waypoints:
                        result = await self.osrm_client.route(
                            waypoints, RoutingProfile.DRIVING
                        )
                        osrm_outputs.append(result)

        route_plan = self.route_assembler.assemble(itinerary, osrm_outputs)

        for day, seg in zip(itinerary.days, route_plan.segments):
            day.route_segment = seg

        return route_plan, warnings
