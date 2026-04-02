"""
Supabase async client — Data API (PostgREST) üzerinden bağlantı.

asyncpg yerine supabase-py kullanılıyor; bu sayede:
  - Port 5432 engeli yok (HTTPS/443 üzerinden)
  - SSL sertifika sorunu yok
  - Connection pool yönetimi supabase-py'a devredildi

Gerekli .env değişkenleri:
  SUPABASE_URL=https://xxx.supabase.co
  SUPABASE_KEY=sb_publishable_...   (anon/publishable key)
"""
from __future__ import annotations

from supabase import AsyncClient, acreate_client


async def create_supabase_client(url: str, key: str) -> AsyncClient:
    """Supabase async client oluşturur."""
    return await acreate_client(url, key)


async def close_supabase_client(client: AsyncClient) -> None:
    """Client kaynakları serbest bırakır (varsa)."""
    try:
        await client.aclose()
    except Exception:
        pass
