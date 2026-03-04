from app.schemas.dtos import (
    RouteRequest, ReplanRequest, PoiQuery,
    TripDaySuggestionRequest, ValidationResult, ApiWarning, Severity
)
from app.core.config import settings


class RequestValidator:
    """Validates incoming API requests at the boundary layer."""

    def __init__(self):
        self.max_trip_days = settings.max_trip_days
        self.max_pois_per_day = settings.max_pois_per_day
        self.min_daily_distance = settings.min_daily_distance_meters
        self.max_category_count = settings.max_category_count

    def validate_route_request(self, req: RouteRequest) -> ValidationResult:
        errors, warnings = [], []

        if req.preferences.trip_days < 1:
            errors.append("trip_days must be at least 1.")
        if req.preferences.trip_days > self.max_trip_days:
            errors.append(f"trip_days cannot exceed {self.max_trip_days}.")
        if req.preferences.max_distance_per_day < self.min_daily_distance:
            errors.append(
                f"max_distance_per_day must be >= {self.min_daily_distance} meters."
            )
        if not req.preferences.city:
            errors.append("city is required.")
        if len(req.preferences.categories) > self.max_category_count:
            errors.append(
                f"categories cannot exceed {self.max_category_count} items."
            )
        if not req.preferences.categories:
            warnings.append(
                ApiWarning(
                    code="NO_CATEGORIES",
                    severity=Severity.WARN,
                    message="No categories specified; all POIs will be considered.",
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_replan_request(self, req: ReplanRequest) -> ValidationResult:
        errors = []

        if not req.existing_itinerary.days:
            errors.append("existing_itinerary must contain at least one day.")

        day_indices = {d.day_index for d in req.existing_itinerary.days}
        for op in req.edits.reorder_operations:
            if op.day_index not in day_indices:
                errors.append(f"Reorder operation references unknown day_index {op.day_index}.")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_poi_query(self, query: PoiQuery) -> ValidationResult:
        errors = []
        if not query.city:
            errors.append("city is required.")
        if len(query.categories) > self.max_category_count:
            errors.append(
                f"categories cannot exceed {self.max_category_count} items."
            )
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_trip_day_suggestion_request(
        self, req: TripDaySuggestionRequest
    ) -> ValidationResult:
        errors = []
        if not req.city:
            errors.append("city is required.")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
