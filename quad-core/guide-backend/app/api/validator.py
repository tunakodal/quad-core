from app.schemas.common import ApiWarning, Severity, ValidationResult
from app.schemas.poi_dtos import PoiQuery
from app.schemas.route_dtos import ReplanRequest, RouteRequest
from app.schemas.suggestion_dtos import TripDaySuggestionRequest
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

        trip_days = req.preferences.trip_days
        max_distance = req.preferences.max_distance_per_day
        city = req.preferences.city
        categories = req.preferences.categories

        if not city:
            errors.append("city is required.")

        if not categories:
            errors.append("categories must not be empty.")

        if len(categories) > self.max_category_count:
            errors.append(
                f"categories cannot exceed {self.max_category_count} items."
            )

        # TC-UT-03: at least one planning constraint must exist
        if trip_days is None and max_distance is None:
            errors.append(
                "At least one planning constraint must be provided: trip_days or max_distance_per_day."
            )

        if trip_days is not None:
            if trip_days < 1:
                errors.append("trip_days must be at least 1.")
            if trip_days > self.max_trip_days:
                errors.append(f"trip_days cannot exceed {self.max_trip_days}.")

        if max_distance is not None:
            if max_distance < self.min_daily_distance:
                errors.append(
                    f"max_distance_per_day must be >= {self.min_daily_distance} meters."
                )

            city_limit = self._get_city_max_distance(city)

            if city_limit is not None and max_distance > city_limit:
                errors.append(
                    f"max_distance_per_day cannot exceed {city_limit} meters for city={city}."
                )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def validate_replan_request(self, req: ReplanRequest) -> ValidationResult:
        errors = []

        if not req.existing_itinerary.days:
            errors.append("existing_itinerary must contain at least one day.")

        day_indices = {d.day_index for d in req.existing_itinerary.days}

        for day_index in (req.edits.ordered_poi_ids_by_day or {}):
            if day_index not in day_indices:
                errors.append(f"ordered_poi_ids_by_day references unknown day_index {day_index}.")

        for op in (getattr(req.edits, "reorder_operations", None) or []):
            if op.day_index not in day_indices:
                errors.append(f"reorder_operations references unknown day_index {op.day_index}.")

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


    def _get_city_max_distance(self, city: str) -> int | None:
        """
        Hook for city-based maximum daily distance.
        Returns None by default; tests or higher-level integrations may override this.
        """
        return None