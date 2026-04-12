"""
Content repository — POI metin açıklamaları.

İki strateji:
  ContentRepository         — JSON dosyasından okur (geliştirme / fallback)
  PostgresContentRepository — Supabase Data API üzerinden okur (production)

DB ↔ domain model farkları:
  poi_contents.poi_id  INTEGER → domain PoiContent.poi_id: str  (int() ile sorgulanır)
  language             Supabase enum string olarak döner (örn. 'EN', 'TR')

Dil stratejisi: önce istenen dil denenir, bulunamazsa EN'e fallback yapılır.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.models.enums import Language
from app.models.media import MediaAsset
from app.models.poi import PoiContent
from app.repositories.interfaces import AbstractContentRepository


# ── JSON / geliştirme implementasyonu ────────────────────────────

class ContentRepository(AbstractContentRepository):
    """
    POI açıklama metinlerini ve görsel metadata'sını JSON dosyasından sağlar.

    İçerik, yükleme sırasında {poi_id → {lang → PoiContent}} yapısına
    çözümlenir; sorgular O(1) dict lookup ile karşılanır.
    """

    def __init__(self, json_path: str):
        # {poi_id: {lang_value: PoiContent}}
        self._contents: dict[str, dict[str, PoiContent]] = {}
        self._load(json_path)

    def _load(self, json_path: str) -> None:
        """JSON dosyasını okur ve bellek içi arama yapısını oluşturur."""
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
        """
        Belirtilen POI ve dil için içerik döner.
        İstenen dil bulunamazsa EN'e fallback yapar; o da yoksa None.
        """
        poi_contents = self._contents.get(poi_id)
        if poi_contents is None:
            return None
        return poi_contents.get(lang.value) or poi_contents.get("EN")

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        """Birden fazla POI için içerik toplu olarak döner. Bulunamayanlar atlanır."""
        result: dict[str, PoiContent] = {}
        for poi_id in poi_ids:
            content = await self.find_content(poi_id, lang)
            if content is not None:
                result[poi_id] = content
        return result


# ── Supabase Data API implementasyonu ────────────────────────────

class PostgresContentRepository(AbstractContentRepository):
    """
    Supabase Data API (PostgREST) üzerinden POI içerik erişimi sağlar.

    Dil stratejisi:
      1. İstenen dil (lang) ile sorgula.
      2. Bulunamazsa EN ile tekrar sorgula.
      3. O da yoksa None döner — üst katman graceful degradation uygular.
    """

    def __init__(self, client):
        self._client = client

    async def find_content(self, poi_id: str, lang: Language) -> PoiContent | None:
        """
        POI için istenen dildeki içeriği döner.
        İstenen dil bulunamazsa EN'e fallback yapar.
        """
        response = await (
            self._client.table("poi_contents")
            .select("poi_id, language, description_text")
            .eq("poi_id", int(poi_id))
            .eq("language", lang.value)
            .limit(1)
            .execute()
        )

        # İstenen dil yoksa EN'e düş (EN için tekrar sorgu gerekmez)
        if not response.data and lang != Language.EN:
            response = await (
                self._client.table("poi_contents")
                .select("poi_id, language, description_text")
                .eq("poi_id", int(poi_id))
                .eq("language", Language.EN.value)
                .limit(1)
                .execute()
            )

        if not response.data:
            return None

        row = response.data[0]
        return PoiContent(
            poi_id=poi_id,
            language=Language(row["language"]),
            description_text=row["description_text"] or "",
            images=[],   # Görseller ayrı media_assets tablosundan çekilir
            audio=None,  # Ses asset'i ContentService tarafından eklenir
        )

    async def find_content_batch(
        self, poi_ids: list[str], lang: Language
    ) -> dict[str, PoiContent]:
        """Birden fazla POI için içerik toplu olarak döner. Bulunamayanlar atlanır."""
        result: dict[str, PoiContent] = {}
        for poi_id in poi_ids:
            content = await self.find_content(poi_id, lang)
            if content is not None:
                result[poi_id] = content
        return result
