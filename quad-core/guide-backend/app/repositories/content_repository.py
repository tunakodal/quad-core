"""
Content repository — Supabase Data API üzerinden POI içerik erişimi.

DB ↔ domain model farkları:
  poi_contents.poi_id  INTEGER → domain PoiContent.poi_id: str  (int() ile sorgulanır)
  language             Supabase enum string olarak döner (örn. 'EN', 'TR')

Dil stratejisi: önce istenen dil denenir, bulunamazsa EN'e fallback yapılır.
"""
from __future__ import annotations

from app.models.enums import Language
from app.models.poi import PoiContent
from app.repositories.interfaces import AbstractContentRepository


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
