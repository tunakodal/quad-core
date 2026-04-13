import asyncio
import pytest

from fastapi.testclient import TestClient

from main import app

from app.services.routing_service import RoutingService, RouteAssembler
from app.schemas.common import ValidationResult
from app.core.containers import create_container
from app.models.domain import Itinerary, DayPlan, Poi, GeoPoint


def make_poi_dict(pid: str):
    return {
        "id": pid,
        "name": f"POI {pid}",
        "category": "Test",
        "main_category_1": "Test",
        "main_category_2": None,
        "sub_category_1": "Test",
        "sub_category_2": None,
        "sub_category_3": None,
        "sub_category_4": None,
        "city": "Istanbul",
        "location": {
            "latitude": 41.0,
            "longitude": 28.9,
        },
        "estimated_visit_duration": 60,
        "google_rating": None,
        "google_reviews_total": None,
    }


import asyncio
from fastapi.testclient import TestClient

from app.core.containers import create_container
from main import app


import pytest
import httpx

from app.core.containers import create_container
from main import app


@pytest.mark.asyncio
async def test_replanning_pipeline_applies_remove_reorder_and_add_consistently():
    """
    IT-13 — Replanning pipeline: client itinerary snapshot and mixed edits
    (remove, reorder, add) are applied consistently.

    Scenario:
    - Existing itinerary snapshot is provided by the client
    - Remove, reorder, and add edits are submitted in a single request

    Expectations:
    - Updated itinerary is returned successfully
    - All intended edits are reflected correctly
    - Response schema remains stable for UI usage
    - No unintended duplication or POI loss occurs
    """

    container = await create_container()
    app.state.container = container

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        base_payload = {
            "preferences": {
                "city": "Istanbul",
                "trip_days": 1,
                "categories": ["Museum"],
                "max_distance_per_day": 10000,
            },
            "constraints": {
                "max_trip_days": 1,
                "max_pois_per_day": 5,
                "max_daily_distance": 10000,
            },
            "language": "EN",
        }

        generate_response = await client.post(
            "/api/v1/routes/generate",
            json=base_payload,
        )
        assert generate_response.status_code == 200

        generated_data = generate_response.json()
        original_itinerary = generated_data["itinerary"]
        original_pois = original_itinerary["days"][0]["pois"]

        assert len(original_pois) >= 2

        original_ids = [poi["id"] for poi in original_pois]
        kept_id = original_ids[0]
        removed_id = original_ids[1]

        search_payload = {
            "city": "Istanbul",
            "categories": ["Museum"],
        }

        search_response = await client.post(
            "/api/v1/pois/search",
            json=search_payload,
        )
        assert search_response.status_code == 200

        search_data = search_response.json()
        candidate_ids = [poi["id"] for poi in search_data["pois"]]

        add_id = next(pid for pid in candidate_ids if pid not in original_ids)

        replan_payload = {
            "existing_itinerary": original_itinerary,
            "constraints": base_payload["constraints"],
            "edits": {
                "removed_poi_ids": [removed_id],
                "ordered_poi_ids_by_day": {
                    "1": [add_id, kept_id]
                }
            },
        }

        replan_response = await client.post(
            "/api/v1/routes/replan",
            json=replan_payload,
        )
        assert replan_response.status_code == 200

        data = replan_response.json()

        assert "itinerary" in data
        assert "route_plan" in data

        updated_days = data["itinerary"]["days"]
        assert len(updated_days) > 0

        updated_pois = updated_days[0]["pois"]
        updated_ids = [poi["id"] for poi in updated_pois]

        assert removed_id not in updated_ids
        assert kept_id in updated_ids
        assert add_id in updated_ids

        assert updated_ids[:2] == [add_id, kept_id]
        assert len(updated_ids) == len(set(updated_ids))


def test_replanning_recomputes_only_affected_day_segments():
    """
    IT-14 — Replanning pipeline must recompute routing only for
    affected day segments.

    Scenario:
    - A multi-day itinerary snapshot is provided
    - Edits affect only one day

    Expectations:
    - Routing is recomputed only for the affected day
    - Unaffected day segments are preserved
    - Response remains stable for UI consumption
    """

    class TrackingOsrmClient:
        def __init__(self):
            self.route_calls = []

        async def route(self, waypoints, profile=None):
            self.route_calls.append(waypoints)
            return type(
                "OsrmResult",
                (),
                {
                    "distance": 2000,
                    "duration": 600,
                    "geometry_encoded": "recomputed_geometry",
                },
            )()

    class ReplanValidator:
        def validate_route_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

        def validate_replan_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

        def validate_trip_day_suggestion_request(self, req):
            return ValidationResult(is_valid=True, errors=[], warnings=[])

    class MinimalPoiService:
        async def get_candidate_pois(self, prefs):
            return []

        async def count_available_pois(self, city, categories):
            return 0

    class ReplanOnlyItineraryService:
        async def replan(self, existing, edits, constraints, prefs):
            new_days = []

            for day in existing.days:
                requested_order = edits.ordered_poi_ids_by_day.get(day.day_index)

                if requested_order is None:
                    new_days.append(day)
                    continue

                poi_map = {poi.id: poi for poi in day.pois}
                reordered = [poi_map[pid] for pid in requested_order if pid in poi_map]

                new_days.append(
                    DayPlan(
                        day_index=day.day_index,
                        pois=reordered,
                        route_segment=day.route_segment,
                    )
                )

            return Itinerary(days=new_days), []

    tracking_osrm = TrackingOsrmClient()

    routing_service = RoutingService(
        osrm_client=tracking_osrm,
        route_assembler=RouteAssembler(),
    )

    container = type("C", (), {})()
    container.validator = ReplanValidator()
    container.poi_service = MinimalPoiService()
    container.itinerary_service = ReplanOnlyItineraryService()
    container.routing_service = routing_service

    app.state.container = container

    client = TestClient(app)

    payload = {
        "existing_itinerary": {
            "days": [
                {
                    "day_index": 1,
                    "pois": [
                        make_poi_dict("p1"),
                        make_poi_dict("p2"),
                    ],
                    "route_segment": {
                        "day_index": 1,
                        "distance": 1111,
                        "duration": 222,
                        "geometry_encoded": "day1_existing",
                    },
                },
                {
                    "day_index": 2,
                    "pois": [
                        make_poi_dict("p3"),
                        make_poi_dict("p4"),
                    ],
                    "route_segment": {
                        "day_index": 2,
                        "distance": 3333,
                        "duration": 444,
                        "geometry_encoded": "day2_existing",
                    },
                },
            ]
        },
        "edits": {
            "ordered_poi_ids_by_day": {
                "1": ["p2", "p1"]
            }
        },
        "constraints": {
            "max_trip_days": 2,
            "max_pois_per_day": 5,
            "max_daily_distance": 10000,
        },
    }

    response = client.post("/api/v1/routes/replan", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "itinerary" in data
    assert "route_plan" in data

    # only one affected day should be recomputed
    assert len(tracking_osrm.route_calls) == 1

    # reordered day should be reflected in response
    updated_day_1_ids = [poi["id"] for poi in data["itinerary"]["days"][0]["pois"]]
    assert updated_day_1_ids == ["p2", "p1"]

    # unaffected day should preserve its previous route segment
    segments = data["route_plan"]["segments"]
    assert len(segments) == 2

    day1_segment = segments[0]
    day2_segment = segments[1]

    assert day1_segment["day_index"] == 1
    assert day1_segment["geometry_encoded"] == "recomputed_geometry"

    assert day2_segment["day_index"] == 2
    assert day2_segment["geometry_encoded"] == "day2_existing"