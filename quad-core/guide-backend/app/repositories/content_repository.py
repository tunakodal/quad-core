"""
Content repository — POI text descriptions and image metadata.

Currently backed by a JSON file.
PostgreSQL implementation is pending — see TODO below.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import PoiContent
from app.repositories.interfaces import AbstractContentRepository


# TODO (Tuna): DB'den çekecek şekilde güncelle.
#   - find_content(poi_id, lang) → SELECT ... FROM poi_contents
#                                   WHERE poi_id=$1 AND language=$2
#   - Bulamazsa language='EN' ile tekrar dene, o da yoksa None döner
#   - find_content_batch → her poi_id için find_content() çağır
#   - Her satırı PoiContent(poi_id, language, description_text, images=[], audio=None) nesnesine dönüştür
class ContentRepository(AbstractContentRepository):
    """Provides POI descriptions and image metadata from a JSON file."""

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
            images = [MediaAsset(**img) for img in item.get("images", [])]
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
        # Exact language match → fallback to EN
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
