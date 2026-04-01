from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────
    database_url: Optional[str] = None
    db_ssl: bool = True          # Supabase ve uzak postgres için True

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


settings = Settings()