import math
import httpx
from app.models.enums import RoutingProfile
from app.models.geo import GeoPoint
from app.core.config import settings


class OsrmRouteResponse:
    """OSRM'den donen rota sonucunu tasir: mesafe, sure, encoded geometri ve nokta sirasi."""
    def __init__(
        self,
        distance: int,
        duration: int,
        geometry_encoded: str,
        waypoint_order: list[int],
    ):
        """Nesneyi baslatir."""
        self.distance = distance
        self.duration = duration
        self.geometry_encoded = geometry_encoded
        self.waypoint_order = waypoint_order


class OsrmClient:

    """OSRM Route ve Trip endpoint'leriyle iletisim kuran asenkron HTTP istemcisi."""
    def __init__(
        self,
        base_url: str = settings.osrm_base_url,
        timeout_ms: int = settings.osrm_timeout_ms,
    ):
        """Nesneyi baslatir."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_ms / 1000

    def _coords_str(self, waypoints: list[GeoPoint]) -> str:
        """Koordinat listesini OSRM formatina (lng,lat;lng,lat) donusturur."""
        return ";".join(f"{p.longitude},{p.latitude}" for p in waypoints)

    @staticmethod
    def _haversine(a: GeoPoint, b: GeoPoint) -> float:
        """Iki koordinat arasindaki kus ucusu mesafesini metre cinsinden hesaplar (Haversine)."""
        R = 6371000
        lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
        dlat = lat2 - lat1
        dlng = math.radians(b.longitude - a.longitude)
        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        return 2 * R * math.asin(math.sqrt(h))

    async def trip(
        self,
        waypoints: list[GeoPoint],
        profile: RoutingProfile = RoutingProfile.DRIVING,
    ) -> OsrmRouteResponse:

        """Verilen noktalari en iyi sirada birbirine baglayan tur rotasini OSRM'den hesaplar."""
        n = len(waypoints)

        if n <= 1:
            return OsrmRouteResponse(
                distance=0,
                duration=0,
                geometry_encoded="",
                waypoint_order=list(range(n)),
            )

        # Kuş uçuşu mesafe hesapla
        crow_total = 0
        for i in range(n - 1):
            crow_total += self._haversine(waypoints[i], waypoints[i + 1])

        route_coords = self._coords_str(waypoints)
        route_url = f"{self.base_url}/route/v1/{profile.value}/{route_coords}"
        route_params = {
            "overview": "full",
            "geometries": "polyline",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(route_url, params=route_params)
            resp.raise_for_status()
            route_data = resp.json()

        route = route_data["routes"][0]
        osrm_distance = int(route["distance"])
        osrm_duration = int(route["duration"])

        # Log
        print(f"\n=== OSRM Route ===")
        print(f"  Waypoints: {n}")
        print(f"  Crow-fly total: {crow_total / 1000:.1f} km")
        print(f"  OSRM distance:  {osrm_distance / 1000:.1f} km")
        print(f"  OSRM duration:  {osrm_duration / 60:.0f} min")
        print(f"  Ratio (road/crow): {osrm_distance / crow_total:.2f}x" if crow_total > 0 else "")

        return OsrmRouteResponse(
            distance=osrm_distance,
            duration=osrm_duration,
            geometry_encoded=route["geometry"],
            waypoint_order=list(range(n)),
        )

    async def route(
        self,
        waypoints: list[GeoPoint],
        profile: RoutingProfile = RoutingProfile.DRIVING,
    ) -> OsrmRouteResponse:
        """Noktalari verilen sirada birbirine baglayan rota hesaplar; sabit sira icin kullanilir."""
        return await self.trip(waypoints, profile)