from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: Optional[str] = None
    osrm_base_url: str = "http://localhost:5000"
    media_root_path: str = "./media"
    max_trip_days: int = 10
    max_pois_per_day: int = 9
    min_daily_distance_meters: int = 1000
    max_category_count: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
