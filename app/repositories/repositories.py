"""
Repository layer — Database Administrator (Erdem) implement edecek.
Bu dosya interface tanımlarını ve stub implementasyonları içerir.
Gerçek DB sorguları PostgreSQL + SQLAlchemy ile buraya yazılacak.
"""
from abc import ABC, abstractmethod
from app.models.domain import Poi, PoiContent, MediaAsset, Language


# ── Interfaces ────────────────────────────────────────────────────

class AbstractPoiRepository(ABC):
    @abstractmethod
    async def find_by_city(self, city: str) -> list[Poi]: ...

    @abstractmethod
    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]: ...

    @abstractmethod
    async def find_by_id(self, poi_id: str) -> Poi | None: ...


class AbstractContentRepository(ABC):
    @abstractmethod
    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None: ...

    @abstractmethod
    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]: ...


class AbstractMediaRepository(ABC):
    @abstractmethod
    async def get_image(self, poi_id: str) -> MediaAsset | None: ...

    @abstractmethod
    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None: ...


class AbstractAudioAssetResolver(ABC):
    @abstractmethod
    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None: ...


# ── Stub implementations (placeholder until DB is ready) ──────────

class StubPoiRepository(AbstractPoiRepository):
    """TODO: Replace with real PostgreSQL implementation."""

    async def find_by_city(self, city: str) -> list[Poi]:
        return []

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        return []

    async def find_by_id(self, poi_id: str) -> Poi | None:
        return None


class StubContentRepository(AbstractContentRepository):
    """TODO: Replace with real PostgreSQL implementation."""

    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        return None

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        return {}


class StubMediaRepository(AbstractMediaRepository):
    """TODO: Replace with real file-system / object storage implementation."""

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return None


class StubAudioAssetResolver(AbstractAudioAssetResolver):
    """TODO: Replace with real asset path resolution."""

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return None
