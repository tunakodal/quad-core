"""
Media repository — image and audio asset resolution.

MediaRepository       — filesystem'den okur (geliştirme / fallback).
PostgresMediaRepository — Supabase/PostgreSQL'den okur (production).

DB şema notu:
  - media_assets.id     → INTEGER (domain asset_id: str, str(id) yapılır)
  - media_assets.poi_id → INTEGER (sorguda int(poi_id) yapılır)
  - media_type/language → PostgreSQL USER-DEFINED enum, ::text cast ile okunur
"""
from __future__ import annotations

from pathlib import Path

from app.models.enums import Language
from app.models.media import MediaAsset
from app.repositories.interfaces import AbstractAudioAssetResolver, AbstractMediaRepository


class MediaRepository(AbstractMediaRepository):
    """
    Resolves static media assets (images and pre-generated TTS audio)
    from the local filesystem under media_root_path.
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
    """Resolves the correct pre-generated audio asset for a POI and language."""

    def __init__(self, media_repository: AbstractMediaRepository):
        self._media_repository = media_repository

    async def resolve_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        return await self._media_repository.get_audio(poi_id, lang)


# ── PostgreSQL implementation ─────────────────────────────────────

class PostgresMediaRepository(AbstractMediaRepository):
    """
    Media repository backed by Supabase/PostgreSQL.

    media_assets tablosundaki url_or_path alanı
    doğrudan MediaAsset.url_or_path olarak kullanılır.
    """

    def __init__(self, pool):
        self._pool = pool

    async def get_image(self, poi_id: str) -> MediaAsset | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, url_or_path, media_type::text AS media_type
            FROM media_assets
            WHERE poi_id = $1
              AND media_type::text = 'image'
            ORDER BY sort_order
            LIMIT 1
            """,
            int(poi_id),
        )
        if row is None:
            return None
        return MediaAsset(
            asset_id=str(row["id"]),
            url_or_path=row["url_or_path"],
            media_type="image",
        )

    async def get_audio(self, poi_id: str, lang: Language) -> MediaAsset | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, url_or_path, media_type::text AS media_type
            FROM media_assets
            WHERE poi_id = $1
              AND media_type::text = 'audio'
              AND language::text = $2
            ORDER BY sort_order
            LIMIT 1
            """,
            int(poi_id),
            lang.value,
        )
        if row is None:
            return None
        return MediaAsset(
            asset_id=str(row["id"]),
            url_or_path=row["url_or_path"],
            media_type="audio",
        )
