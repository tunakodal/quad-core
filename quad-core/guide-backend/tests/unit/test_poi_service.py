"""
Unit tests for PoiService and PoiRepository filtering logic.
Covers TC-UT-06 and TC-UT-07 from the GUIDE Test Plan.

Repositories are replaced with in-memory stubs — no filesystem access.
"""
import pytest

from app.models.domain import Poi, GeoPoint
from app.repositories.repositories import AbstractPoiRepository
from app.schemas.dtos import TravelConstraints, TravelPreferences
from app.services.poi_service import PoiService


pytestmark = pytest.mark.asyncio

# ── In-memory stub repository ──────────────────────────────────────────────────

class InMemoryPoiRepository(AbstractPoiRepository):
    """Minimal in-memory repository for unit tests."""

    def __init__(self, pois: list[Poi]):
        self._pois = pois

    async def find_by_city(self, city: str) -> list[Poi]:
        return [p for p in self._pois if p.city.lower() == city.lower()]

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        city_pois = await self.find_by_city(city)
        if not categories:
            return city_pois
        cat_lower = {c.lower() for c in categories}
        return [
            p for p in city_pois
            if {
                   c.lower()
                   for c in [p.sub_category_1, p.sub_category_2, p.sub_category_3, p.sub_category_4]
                   if c
               } & cat_lower
        ]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        return next((p for p in self._pois if p.id == poi_id), None)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def all_pois(istanbul_pois, ankara_pois) -> list[Poi]:
    """Combined dataset with both Istanbul and Ankara POIs."""
    return istanbul_pois + ankara_pois


@pytest.fixture
def service(all_pois) -> PoiService:
    repo = InMemoryPoiRepository(all_pois)
    return PoiService(repo)


# ── TC-UT-06: City filtering ───────────────────────────────────────────────────

async def test_get_candidates_returns_only_requested_city(service):
    """TC-UT-06 — All returned POIs must belong to the requested city."""
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=[],
        max_distance_per_day=50_000,
    )
    pois = await service.get_candidate_pois(prefs)

    assert len(pois) > 0
    assert all(p.city == "Istanbul" for p in pois)


async def test_get_candidates_excludes_other_cities(service):
    """City filter must not include POIs from other cities."""
    prefs = TravelPreferences(
        city="Ankara",
        trip_days=1,
        categories=[],
        max_distance_per_day=50_000,
    )
    pois = await service.get_candidate_pois(prefs)

    assert all(p.city == "Ankara" for p in pois)
    assert not any(p.city == "Istanbul" for p in pois)


async def test_get_candidates_unknown_city_returns_empty(service):
    """An unknown city should return an empty list."""
    prefs = TravelPreferences(
        city="Atlantis",
        trip_days=1,
        categories=[],
        max_distance_per_day=50_000,
    )
    pois = await service.get_candidate_pois(prefs)

    assert pois == []


# ── TC-UT-07: Category filtering ──────────────────────────────────────────────

async def test_get_candidates_returns_only_selected_categories(service):
    """TC-UT-07 — All returned POIs must belong to one of the selected categories."""
    selected = ["Museum", "Nature"]
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=selected,
        max_distance_per_day=50_000,
    )
    pois = await service.get_candidate_pois(prefs)

    assert len(pois) > 0
    assert all(
        any(
            c in selected
            for c in [
                p.sub_category_1,
                p.sub_category_2,
                p.sub_category_3,
                p.sub_category_4,
            ]
            if c
        )
        for p in pois
    )


async def test_get_candidates_no_categories_returns_all_city_pois(service, istanbul_pois):
    """Empty category list must return all POIs for the city (no category filter)."""
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=[],
        max_distance_per_day=50_000,
    )
    pois = await service.get_candidate_pois(prefs)

    assert len(pois) == len(istanbul_pois)


async def test_get_candidates_nonexistent_category_returns_empty(service):
    """A category with no matching POIs returns an empty list."""
    prefs = TravelPreferences(
        city="Istanbul",
        trip_days=1,
        categories=["Underwater Disco"],
        max_distance_per_day=50_000,
    )
    pois = await service.get_candidate_pois(prefs)

    assert pois == []

# ── count_available_pois ───────────────────────────────────────────────────────

async def test_count_available_pois_matches_filter_result(service):
    """count_available_pois must agree with get_candidate_pois for the same inputs."""
    city, categories = "Istanbul", ["Historical"]
    prefs = TravelPreferences(city=city, trip_days=1, categories=categories, max_distance_per_day=50_000)

    pois = await service.get_candidate_pois(prefs)
    count = await service.count_available_pois(city, categories)

    assert count == len(pois)


async def test_count_available_pois_unknown_city_returns_zero(service):
    count = await service.count_available_pois("Nowhere", ["Historical"])
    assert count == 0
