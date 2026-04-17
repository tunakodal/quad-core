"""
In-memory stub implementations — for unit tests and isolated development.
"""
from __future__ import annotations

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import Poi, PoiContent
from app.repositories.interfaces import (
    AbstractAudioAssetResolver,
    AbstractContentRepository,
    AbstractMediaRepository,
    AbstractPoiRepository,
)


class StubPoiRepository(AbstractPoiRepository):
    """Her zaman boş sonuç dönen POI repository test double'ı."""

    async def find_by_city(self, city: str) -> list[Poi]:
        """Test double — her zaman boş liste döner."""
        return []

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        """Test double — her zaman boş liste döner."""
        return []

    async def find_by_id(self, poi_id: str) -> Poi | None:
        """Test double — her zaman None döner."""
        return None

    async def find_random(self, limit: int) -> list[Poi]:
        """Test double — her zaman boş liste döner."""
        return []


class StubContentRepository(AbstractContentRepository):
    """Her zaman boş sonuç dönen içerik repository test double'ı."""

    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        """Test double — her zaman None döner."""
        return None

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        """Test double — her zaman boş dict döner."""
        return {}


class StubMediaRepository(AbstractMediaRepository):
    """Her zaman boş sonuç dönen medya repository test double'ı."""

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """Test double — her zaman None döner."""
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Test double — her zaman None döner."""
        return None


class StubAudioAssetResolver(AbstractAudioAssetResolver):
    """Her zaman None dönen ses asset çözümleyici test double'ı."""

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Test double — her zaman None döner."""
        return None
