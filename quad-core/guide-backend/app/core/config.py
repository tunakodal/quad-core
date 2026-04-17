from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide configuration settings.

    Values are read from the .env file or environment variables.
    Supabase and OSRM connections are optional; if not set, the app
    falls back to JSON-file-based development mode.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # -- Supabase --
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None  # anon/publishable key

    # -- OSRM --
    osrm_base_url: str = "http://localhost:5000"
    osrm_timeout_ms: int = 5000

    # -- Media --
    media_root_path: str = "./media"

    # -- Trip planning limits --
    max_trip_days: int = 10
    max_pois_per_day: int = 9
    max_total_pois: int = 110
    min_daily_distance_meters: int = 1000
    max_category_count: int = 15
    pois_per_day_baseline: int = 3


settings = Settings()
