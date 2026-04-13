"""
Shared pytest fixtures for the GUIDE backend test suite.

All fixtures use in-memory data — no filesystem or network access required.
"""
import pytest

from app.models.domain import (
    Poi, GeoPoint, Itinerary, DayPlan,
    PoiContent, MediaAsset, Language,
)
from app.schemas.dtos import TravelPreferences, TravelConstraints


# ── POI Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def istanbul_pois() -> list[Poi]:
    """10 mixed-category Istanbul POIs for general itinerary tests."""
    data = [
        {
            "id": "ist-001",
            "name": "Hagia Sophia",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Religious",
            "sub_category_2": "Urban & Monumental Heritage",
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0086,
            "lng": 28.9802,
            "duration": 90,
        },
        {
            "id": "ist-002",
            "name": "Topkapi Palace",
            "category": "Museums",
            "main_category_1": "Museums",
            "main_category_2": None,
            "sub_category_1": "Museum",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0115,
            "lng": 28.9834,
            "duration": 120,
        },
        {
            "id": "ist-003",
            "name": "Blue Mosque",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Religious",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0054,
            "lng": 28.9768,
            "duration": 60,
        },
        {
            "id": "ist-004",
            "name": "Galata Tower",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Urban & Monumental Heritage",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0256,
            "lng": 28.9744,
            "duration": 60,
        },
        {
            "id": "ist-005",
            "name": "Basilica Cistern",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Ancient & Archaeology",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0084,
            "lng": 28.9779,
            "duration": 45,
        },
        {
            "id": "ist-006",
            "name": "Istanbul Archaeology Museums",
            "category": "Museums",
            "main_category_1": "Museums",
            "main_category_2": None,
            "sub_category_1": "Museum",
            "sub_category_2": "Ancient & Archaeology",
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0133,
            "lng": 28.9843,
            "duration": 90,
        },
        {
            "id": "ist-007",
            "name": "Bosphorus Cruise",
            "category": "Nature",
            "main_category_1": "Nature",
            "main_category_2": None,
            "sub_category_1": "Water & Coastal",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0082,
            "lng": 28.9784,
            "duration": 120,
        },
        {
            "id": "ist-008",
            "name": "Grand Bazaar",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Urban & Monumental Heritage",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0107,
            "lng": 28.9680,
            "duration": 90,
        },
        {
            "id": "ist-009",
            "name": "Spice Bazaar",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Urban & Monumental Heritage",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0165,
            "lng": 28.9703,
            "duration": 45,
        },
        {
            "id": "ist-010",
            "name": "Gulhane Park",
            "category": "Nature",
            "main_category_1": "Nature",
            "main_category_2": None,
            "sub_category_1": "Parks & Outdoor",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 41.0135,
            "lng": 28.9832,
            "duration": 45,
        },
    ]

    return [
        Poi(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            main_category_1=item["main_category_1"],
            main_category_2=item["main_category_2"],
            sub_category_1=item["sub_category_1"],
            sub_category_2=item["sub_category_2"],
            sub_category_3=item["sub_category_3"],
            sub_category_4=item["sub_category_4"],
            city="Istanbul",
            location=GeoPoint(latitude=item["lat"], longitude=item["lng"]),
            estimated_visit_duration=item["duration"],
            google_rating=None,
            google_reviews_total=None,
        )
        for item in data
    ]


@pytest.fixture
def ankara_pois() -> list[Poi]:
    """5 Ankara POIs for cross-city filtering tests."""
    data = [
        {
            "id": "ank-001",
            "name": "Ataturk Mausoleum",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Urban & Monumental Heritage",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 39.9258,
            "lng": 32.8371,
            "duration": 90,
        },
        {
            "id": "ank-002",
            "name": "Ankara Castle",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Fortifications",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 39.9407,
            "lng": 32.8637,
            "duration": 60,
        },
        {
            "id": "ank-003",
            "name": "Museum of Anatolian Civilizations",
            "category": "Museums",
            "main_category_1": "Museums",
            "main_category_2": None,
            "sub_category_1": "Museum",
            "sub_category_2": "Ancient & Archaeology",
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 39.9402,
            "lng": 32.8638,
            "duration": 120,
        },
        {
            "id": "ank-004",
            "name": "Atakule Tower",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Urban & Monumental Heritage",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 39.8802,
            "lng": 32.8541,
            "duration": 30,
        },
        {
            "id": "ank-005",
            "name": "Haci Bayram Mosque",
            "category": "Cultural Heritage",
            "main_category_1": "Cultural Heritage",
            "main_category_2": None,
            "sub_category_1": "Religious",
            "sub_category_2": None,
            "sub_category_3": None,
            "sub_category_4": None,
            "lat": 39.9407,
            "lng": 32.8598,
            "duration": 45,
        },
    ]

    return [
        Poi(
            id=item["id"],
            name=item["name"],
            category=item["category"],
            main_category_1=item["main_category_1"],
            main_category_2=item["main_category_2"],
            sub_category_1=item["sub_category_1"],
            sub_category_2=item["sub_category_2"],
            sub_category_3=item["sub_category_3"],
            sub_category_4=item["sub_category_4"],
            city="Ankara",
            location=GeoPoint(latitude=item["lat"], longitude=item["lng"]),
            estimated_visit_duration=item["duration"],
            google_rating=None,
            google_reviews_total=None,
        )
        for item in data
    ]


@pytest.fixture
def single_poi(istanbul_pois) -> Poi:
    return istanbul_pois[0]


# ── Constraints & Preferences Fixtures ────────────────────────────────────────

@pytest.fixture
def default_constraints() -> TravelConstraints:
    return TravelConstraints(
        max_trip_days=3,
        max_pois_per_day=3,
        max_daily_distance=100_000,
    )


@pytest.fixture
def tight_constraints() -> TravelConstraints:
    """Only 1 POI per day — useful for edge-case allocation tests."""
    return TravelConstraints(
        max_trip_days=2,
        max_pois_per_day=1,
        max_daily_distance=50_000,
    )


@pytest.fixture
def default_prefs() -> TravelPreferences:
    return TravelPreferences(
        city="Istanbul",
        trip_days=3,
        categories=["Museum", "Religious"],
        max_distance_per_day=50_000,
    )


# ── Itinerary Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_itinerary(istanbul_pois, default_constraints) -> Itinerary:
    """A 3-day itinerary built from the first 9 Istanbul POIs (3 per day)."""
    from app.services.itinerary_service import ItineraryBuilder
    builder = ItineraryBuilder()
    return builder.allocate_to_days(istanbul_pois[:9], default_constraints)


@pytest.fixture
def single_day_itinerary(istanbul_pois) -> Itinerary:
    """Single-day itinerary with 3 POIs."""
    return Itinerary(days=[
        DayPlan(day_index=1, pois=istanbul_pois[:3])
    ])


# ── Content Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_content() -> PoiContent:
    return PoiContent(
        poi_id="ist-001",
        language=Language.EN,
        description_text="Hagia Sophia is one of Istanbul's most iconic landmarks.",
        images=[
            MediaAsset(asset_id="img-001", url_or_path="/media/images/ist-001/01.jpg", media_type="image")
        ],
        audio=None,
    )


@pytest.fixture
def sample_audio_asset() -> MediaAsset:
    return MediaAsset(
        asset_id="audio-001-en",
        url_or_path="/media/audio/ist-001/en.mp3",
        media_type="audio",
    )