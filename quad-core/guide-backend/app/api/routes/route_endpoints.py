"""
Route Endpoints — API Boundary for route generation, replanning, and trip-day suggestion.

Aligned with GUIDE LLD: RouteController class (Appendix A.1.1).
Dependencies are resolved from the application container at request time.
"""
from fastapi import APIRouter, HTTPException, Request

from app.schemas.dtos import (
    RouteRequest, RouteResponse,
    ReplanRequest, TripDaySuggestionRequest, TripDaySuggestionResponse,
    ApiErrorResponse, TravelPreferences,
)
from app.api.validator import RequestValidator
from app.services.itinerary_service import ItineraryService
from app.services.routing_service import RoutingService
from app.services.poi_service import PoiService
from app.core.config import settings

router = APIRouter(prefix="/routes", tags=["Routes"])

_ERROR_RESPONSES = {
    400: {"model": ApiErrorResponse},
    404: {"model": ApiErrorResponse},
    422: {"model": ApiErrorResponse},
    500: {"model": ApiErrorResponse},
}


class RouteController:
    """
    Handles route generation and replanning endpoints by validating requests,
    orchestrating itinerary and routing services, and returning a normalized
    API response (including warnings) in a stateless workflow.

    Aligned with LLD RouteController interface (Appendix A.1.1).
    """

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

        # Derive city from existing itinerary
        city = "unknown"
        if req.existing_itinerary.days:
            first_day = req.existing_itinerary.days[0]
            if first_day.pois:
                city = first_day.pois[0].city

        prefs = TravelPreferences(
            city=city,
            trip_days=req.constraints.max_trip_days,
            categories=[],
            max_distance_per_day=req.constraints.max_daily_distance,
        )

        itinerary = await self._itinerary_service.replan(
            req.existing_itinerary, req.edits, req.constraints, prefs
        )
        route_plan = await self._routing_service.update_route_after_edits(itinerary, req.edits)

        return RouteResponse(
            itinerary=itinerary,
            route_plan=route_plan,
            warnings=validation.warnings,
        )

    async def suggest_trip_days(
        self, req: TripDaySuggestionRequest
    ) -> TripDaySuggestionResponse:
        """Suggest max feasible trip days based on available POIs."""
        validation = self._validator.validate_trip_day_suggestion_request(req)
        if not validation.is_valid:
            raise HTTPException(status_code=422, detail=validation.errors)

        count = await self._poi_service.count_available_pois(req.city, req.categories)

        max_days = min(
            count // settings.pois_per_day_baseline,
            settings.max_trip_days
        )

        return TripDaySuggestionResponse(
            max_recommended_days=max(max_days, 1),
            poi_count=count,
            warnings=validation.warnings,
        )


# ── Lazy controller accessor ──────────────────────────────────────

def _get_controller(request: Request) -> RouteController:
    """Resolve RouteController from the application DI container."""
    container = request.app.state.container
    return RouteController(
        validator=container.validator,
        poi_service=container.poi_service,
        itinerary_service=container.itinerary_service,
        routing_service=container.routing_service,
    )


# ── Endpoint wrappers ─────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=RouteResponse,
    responses=_ERROR_RESPONSES,
    summary="Generate a multi-day itinerary and route",
)
async def generate_route(req: RouteRequest, request: Request):
    return await _get_controller(request).generate_route(req)


@router.post(
    "/replan",
    response_model=RouteResponse,
    responses=_ERROR_RESPONSES,
    summary="Replan itinerary after user edits",
)
async def replan_route(req: ReplanRequest, request: Request):
    return await _get_controller(request).replan_route(req)


@router.post(
    "/suggest-days",
    response_model=TripDaySuggestionResponse,
    responses=_ERROR_RESPONSES,
    summary="Suggest max feasible trip days",
)
async def suggest_trip_days(req: TripDaySuggestionRequest, request: Request):
    return await _get_controller(request).suggest_trip_days(req)
