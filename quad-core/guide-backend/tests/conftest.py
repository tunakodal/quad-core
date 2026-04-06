"""
Shared pytest fixtures for the GUIDE backend test suite.

All fixtures use in-memory data — no filesystem or network access required.
"""
import pytest

from app.models.domain import (
    Poi, GeoPoint, Itinerary, DayPlan, RouteSegment,
    PoiContent, MediaAsset, Language,
)
from app.schemas.dtos import TravelPreferences, TravelConstraints


# ── POI Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def istanbul_pois() -> list[Poi]:
    """10 mixed-category Istanbul POIs for general itinerary tests."""
    data = [
        ("ist-001", "Hagia Sophia",      "Historical", 41.0086, 28.9802, 90),
        ("ist-002", "Topkapi Palace",     "Historical", 41.0115, 28.9834, 120),
        ("ist-003", "Blue Mosque",        "Historical", 41.0054, 28.9768, 60),
        ("ist-004", "Galata Tower",       "Historical", 41.0256, 28.9744, 60),
        ("ist-005", "Basilica Cistern",   "Historical", 41.0084, 28.9779, 45),
        ("ist-006", "Istanbul Arch. Mus", "Museum",     41.0133, 28.9843, 90),
        ("ist-007", "Bosphorus Cruise",   "Nature",     41.0082, 28.9784, 120),
        ("ist-008", "Grand Bazaar",       "Shopping",   41.0107, 28.9680, 90),
        ("ist-009", "Spice Bazaar",       "Shopping",   41.0165, 28.9703, 45),
        ("ist-010", "Gulhane Park",       "Nature",     41.0135, 28.9832, 45),
    ]
    return [
        Poi(
            id=pid, name=name, category=cat, city="Istanbul",
            location=GeoPoint(latitude=lat, longitude=lng),
            estimated_visit_duration=dur,
        )
        for pid, name, cat, lat, lng, dur in data
    ]


@pytest.fixture
def ankara_pois() -> list[Poi]:
    """5 Ankara POIs for cross-city filtering tests."""
    data = [
        ("ank-001", "Ataturk Mausoleum",        "Historical", 39.9258, 32.8371, 90),
        ("ank-002", "Ankara Castle",             "Historical", 39.9407, 32.8637, 60),
        ("ank-003", "Museum of Anatolian Civ.",  "Museum",     39.9402, 32.8638, 120),
        ("ank-004", "Atakule Tower",             "Landmark",   39.8802, 32.8541, 30),
        ("ank-005", "Haci Bayram Mosque",        "Historical", 39.9407, 32.8598, 45),
    ]
    return [
        Poi(
            id=pid, name=name, category=cat, city="Ankara",
            location=GeoPoint(latitude=lat, longitude=lng),
            estimated_visit_duration=dur,
        )
        for pid, name, cat, lat, lng, dur in data
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
        categories=["Historical", "Museum"],
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
