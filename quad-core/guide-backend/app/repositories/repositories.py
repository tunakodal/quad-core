"""
Data Access Layer — Repository and DataSource implementations.

Aligned with GUIDE Low-Level Design Document (Appendix A.1.4).
Provides read-only access to POI metadata, content, and media assets.
Storage mechanism is abstracted via the DataSource interface.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.domain import Poi, PoiContent, MediaAsset, Language, GeoPoint
from app.core.config import settings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DataSource Interface (LLD A.1.4)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AbstractDataSource(ABC):
    """Abstracts the underlying POI storage mechanism (JSON, CSV, database)."""

    @abstractmethod
    def load_all_pois(self) -> list[Poi]: ...

    @abstractmethod
    def load_by_id(self, poi_id: str) -> Poi | None: ...


class JsonDataSource(AbstractDataSource):
    """Loads POI records from a JSON file on disk."""

    def __init__(self, json_path: str):
        self._pois: list[Poi] = []
        self._index: dict[str, Poi] = {}
        self._load(json_path)

    def _load(self, json_path: str) -> None:
        path = Path(json_path)
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            poi = Poi(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                city=item["city"],
                location=GeoPoint(
                    latitude=item["location"]["latitude"],
                    longitude=item["location"]["longitude"],
                ),
                estimated_visit_duration=item["estimated_visit_duration"],
            )
            self._pois.append(poi)
            self._index[poi.id] = poi

    def load_all_pois(self) -> list[Poi]:
        return list(self._pois)

    def load_by_id(self, poi_id: str) -> Poi | None:
        return self._index.get(poi_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Repository Interfaces (abstract)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Concrete Implementations — JSON / File-System based
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PoiRepository(AbstractPoiRepository):
    """
    Provides access to curated POI metadata.
    Delegates storage to a DataSource implementation.
    """

    def __init__(self, data_source: AbstractDataSource):
        self._data_source = data_source

    async def find_by_city(self, city: str) -> list[Poi]:
        all_pois = self._data_source.load_all_pois()
        return [p for p in all_pois if p.city.lower() == city.lower()]

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        city_pois = await self.find_by_city(city)
        if not categories:
            return city_pois
        cat_lower = {c.lower() for c in categories}
        return [p for p in city_pois if p.category.lower() in cat_lower]

    async def find_by_id(self, poi_id: str) -> Poi | None:
        return self._data_source.load_by_id(poi_id)


class ContentRepository(AbstractContentRepository):
    """
    Provides destination descriptions and image/audio metadata for POIs.
    Loaded from a JSON file.
    """

    def __init__(self, json_path: str):
        self._contents: dict[str, dict[str, PoiContent]] = {}
        self._load(json_path)

    def _load(self, json_path: str) -> None:
        path = Path(json_path)
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for item in raw:
            poi_id = item["poi_id"]
            lang_str = item.get("language", "EN")
            images = [
                MediaAsset(**img)
                for img in item.get("images", [])
            ]
            content = PoiContent(
                poi_id=poi_id,
                language=Language(lang_str),
                description_text=item.get("description_text", ""),
                images=images,
                audio=None,
            )
            if poi_id not in self._contents:
                self._contents[poi_id] = {}
            self._contents[poi_id][lang_str] = content

    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        poi_contents = self._contents.get(poi_id)
        if poi_contents is None:
            return None
        # Try exact language match, then fallback to EN
        result = poi_contents.get(lang.value)
        if result is None:
            result = poi_contents.get("EN")
        return result

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        result: dict[str, PoiContent] = {}
        for poi_id in poi_ids:
            content = await self.find_content(poi_id, lang)
            if content is not None:
                result[poi_id] = content
        return result


class MediaRepository(AbstractMediaRepository):
    """
    Provides access to static media assets (images and pre-generated TTS audio).
    Resolves asset paths/URLs based on POI identifiers and language selection.
    """

    def __init__(self, media_root_path: str):
        self._media_root = Path(media_root_path)

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        img_dir = self._media_root / "images" / poi_id
        if img_dir.exists():
            for ext in ("jpg", "png", "webp"):
                candidate = img_dir / f"01.{ext}"
                if candidate.exists():
                    return MediaAsset(
                        asset_id=f"{poi_id}-img-01",
                        url_or_path=str(candidate),
                        media_type="image",
                    )
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        audio_dir = self._media_root / "audio" / poi_id
        lang_lower = lang.value.lower()
        for ext in ("mp3", "wav", "ogg"):
            candidate = audio_dir / f"{lang_lower}.{ext}"
            if candidate.exists():
                return MediaAsset(
                    asset_id=f"{poi_id}-audio-{lang_lower}",
                    url_or_path=str(candidate),
                    media_type="audio",
                )
        return None


class AudioAssetResolver(AbstractAudioAssetResolver):
    """
    Resolves the correct pre-generated audio asset for a POI and language selection.
    Delegates to MediaRepository for actual file resolution.
    """

    def __init__(self, media_repository: AbstractMediaRepository):
        self._media_repository = media_repository

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return await self._media_repository.get_audio(poi_id, lang)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Stub implementations (kept for backward compatibility / testing)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class StubPoiRepository(AbstractPoiRepository):
    """Empty stub — useful for unit tests with mocked data."""

    async def find_by_city(self, city: str) -> list[Poi]:
        return []

    async def find_by_city_and_categories(
        self, city: str, categories: list[str]
    ) -> list[Poi]:
        return []

    async def find_by_id(self, poi_id: str) -> Poi | None:
        return None


class StubContentRepository(AbstractContentRepository):
    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        return None

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        return {}


class StubMediaRepository(AbstractMediaRepository):
    async def get_image(self, poi_id: str) -> MediaAsset | None:
        return None

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return None


class StubAudioAssetResolver(AbstractAudioAssetResolver):
    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return None
