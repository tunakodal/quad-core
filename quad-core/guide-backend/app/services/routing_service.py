from app.models.enums import RoutingProfile
from app.models.route import Itinerary, RoutePlan, RouteSegment
from app.schemas.route_dtos import UserEdits
from app.schemas.travel import TravelConstraints
from app.integration.osrm_client import OsrmClient, OsrmRouteResponse
from app.schemas.common import ApiWarning


class RouteAssembler:

    def assemble(self, itinerary: Itinerary, osrm_outputs) -> RoutePlan:
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

    def __init__(self, osrm_client: OsrmClient, route_assembler: RouteAssembler):
        self.osrm_client = osrm_client
        self.route_assembler = route_assembler

    async def generate_route(
        self, itinerary: Itinerary, constraints: TravelConstraints
    ) -> tuple[RoutePlan, list[ApiWarning]]:
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

        warnings: list[ApiWarning] = []
        affected_days = set(edits.ordered_poi_ids_by_day.keys())

        osrm_outputs = []

        for day in itinerary.days:
            if day.day_index in affected_days:
                # Modified gün — frontend sırasıyla route al
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
                # Değişmemiş gün — mevcut segment'i koru
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