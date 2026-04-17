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
    """Test dubloru: her zaman bos sonuc doner."""
    async def find_by_city(self, city: str) -> list[Poi]:
        """Test dubloru -- her zaman bos liste doner."""
        return []

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        """Test dubloru -- her zaman bos liste doner."""
        return []

    async def find_by_id(self, poi_id: str) -> Poi | None:
        """Test dubloru -- her zaman None doner."""
        return None


class StubContentRepository(AbstractContentRepository):
    """Test dubloru: her zaman bos sonuc doner."""
    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        """Test dubloru -- her zaman None doner."""
        return None

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        """Test dubloru -- her zaman bos dict doner."""
        return {}


class StubMediaRepository(AbstractMediaRepository):
    """Test dubloru: her zaman bos sonuc doner."""
    async def get_image(self, poi_id: str) -> MediaAsset | None:
        """Test dubloru -- her zaman None doner."""
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Test dubloru -- her zaman None doner."""
        return None


class StubAudioAssetResolver(AbstractAudioAssetResolver):
    """Test dubloru: her zaman None doner."""
    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        """Test dubloru -- her zaman None doner."""
        return None
