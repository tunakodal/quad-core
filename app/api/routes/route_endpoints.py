from fastapi import APIRouter, HTTPException
from app.schemas.dtos import (
    RouteRequest, RouteResponse,
    ReplanRequest, TripDaySuggestionRequest, TripDaySuggestionResponse,
    ApiErrorResponse,
)
from app.api.validator import RequestValidator
from app.services.itinerary_service import (
    ItineraryService, ItineraryBuilder,
    MonteCarloItineraryPlanner, HeuristicPlanRanker,
)
from app.services.routing_service import RoutingService, RouteAssembler
from app.services.poi_service import PoiService
from app.repositories.repositories import StubPoiRepository
from app.integration.osrm_client import OsrmClient

router = APIRouter(prefix="/routes", tags=["Routes"])

# Dependency wiring (will be replaced with proper DI / lifespan)
_poi_repo = StubPoiRepository()
_poi_service = PoiService(_poi_repo)
_builder = ItineraryBuilder()
_ranker = HeuristicPlanRanker()
_planner = MonteCarloItineraryPlanner(_builder, _ranker)
_itinerary_service = ItineraryService(_planner)
_osrm = OsrmClient()
_assembler = RouteAssembler()
_routing_service = RoutingService(_osrm, _assembler)
_validator = RequestValidator()

_ERROR_RESPONSES = {
    400: {"model": ApiErrorResponse},
    404: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
    500: {"model": ApiErrorResponse},
}


class RouteController:
    def __init__(
        self,
        validator: RequestValidator,
        poi_service: PoiService,
        itinerary_service: ItineraryService,
        routing_service: RoutingService,
    ):
        self._validator = validator
        self._poi_service = poi_service
        self._itinerary_service = itinerary_service
        self._routing_service = routing_service

    async def generate_route(self, req: RouteRequest) -> RouteResponse:
        """Generate a multi-day itinerary from user preferences."""
        validation = self._validator.validate_route_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        pois = await self._poi_service.get_candidate_pois(req.preferences)
        pois = await self._poi_service.filter_by_constraints(pois, req.constraints)

        if len(pois) < 2:
            raise HTTPException(
                status_code=400,
                detail="Not enough POIs match the given filters. Try adjusting categories or city.",
            )

        itinerary = await self._itinerary_service.build_itinerary(
            pois, req.constraints, req.preferences
        )
        route_plan = await self._routing_service.generate_route(itinerary, req.constraints)

        return RouteResponse(
            itinerary=itinerary,
            route_plan=route_plan,
            warnings=validation.warnings,
            effective_trip_days=len(itinerary.days),
        )

    async def replan_route(self, req: ReplanRequest) -> RouteResponse:
        """Replan an existing itinerary after user edits (stateless)."""
        validation = self._validator.validate_replan_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        # Rebuild preferences from constraints for scoring (minimal)
        from app.schemas.dtos import TravelPreferences

        prefs = TravelPreferences(
            city="unknown",
            trip_days=req.constraints.max_trip_days,
            categories=[],
            max_distance_per_day=req.constraints.max_daily_distance,
        )

        itinerary = await self._itinerary_service.replan(
            req.existing_itinerary, req.edits, req.constraints, prefs
        )
        route_plan = await self._routing_service.update_route_after_edits(itinerary, req.edits)

        return RouteResponse(itinerary=itinerary, route_plan=route_plan)

    async def suggest_trip_days(
        self, req: TripDaySuggestionRequest
    ) -> TripDaySuggestionResponse:
        """Suggest max feasible trip days based on available POIs."""
        validation = self._validator.validate_trip_day_suggestion_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        count = await self._poi_service.count_available_pois(req.city, req.categories)
        from app.core.config import settings

        max_days = min(count // 3, settings.max_trip_days)  # ~3 POIs/day baseline

        return TripDaySuggestionResponse(
            max_recommended_days=max(max_days, 1),
            poi_count=count,
            warnings=validation.warnings,
        )


_controller = RouteController(
    validator=_validator,
    poi_service=_poi_service,
    itinerary_service=_itinerary_service,
    routing_service=_routing_service,
)

router.add_api_route(
    "/generate",
    _controller.generate_route,
    methods=["POST"],
    response_model=RouteResponse,
    responses=_ERROR_RESPONSES,
)
router.add_api_route(
    "/replan",
    _controller.replan_route,
    methods=["POST"],
    response_model=RouteResponse,
    responses=_ERROR_RESPONSES,
)
router.add_api_route(
    "/suggest-days",
    _controller.suggest_trip_days,
    methods=["POST"],
    response_model=TripDaySuggestionResponse,
    responses=_ERROR_RESPONSES,
)
