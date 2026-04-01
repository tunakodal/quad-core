"""
Database connection — asyncpg connection pool.

Şifrede özel karakter varsa (örn. '?') DATABASE_URL'de URL-encode et:
  ? → %3F
  @ → %40
  # → %23

Örnek .env:
  DATABASE_URL=postgresql://postgres:sifre%3F@host:5432/postgres
  DB_SSL=true
"""
from __future__ import annotations

import ssl
from urllib.parse import unquote, urlparse

import asyncpg


async def create_pool(database_url: str, use_ssl: bool = True) -> asyncpg.Pool:
    """
    asyncpg bağlantı havuzu oluşturur.

    DATABASE_URL'deki şifre URL-encoded olabilir (örn. %3F → ?),
    bu fonksiyon otomatik olarak decode eder.
    """
    parsed = urlparse(database_url)

    ssl_ctx: ssl.SSLContext | bool | None
    if use_ssl:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
    else:
        ssl_ctx = None

    pool = await asyncpg.create_pool(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=unquote(parsed.password or ""),
        database=parsed.path.lstrip("/"),
        ssl=ssl_ctx,
        min_size=1,
        max_size=10,
    )
    return pool


async def close_pool(pool: asyncpg.Pool) -> None:
    """Bağlantı havuzunu güvenli şekilde kapatır."""
    await pool.close()
