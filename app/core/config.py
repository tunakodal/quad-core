from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── Supabase ──────────────────────────────────────────────────
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None  # anon/publishable key

    # ── OSRM ─────────────────────────────────────────────────────
    osrm_base_url: str = "http://localhost:5000"
    osrm_timeout_ms: int = 5000

    # ── Media ─────────────────────────────────────────────────────
    media_root_path: str = "./media"

    # ── Trip planning limits ──────────────────────────────────────
    max_trip_days: int = 10
    max_pois_per_day: int = 9
    max_total_pois: int = 90
    min_daily_distance_meters: int = 1000
    max_category_count: int = 10
    pois_per_day_baseline: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
