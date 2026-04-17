"""
Travel preferences and constraints — user inputs that drive route generation.
"""
from pydantic import BaseModel, Field


class TravelPreferences(BaseModel):
    """Kullanicinin gezi tercihlerini icerir: sehir, sure, kategoriler ve gunluk mesafe limiti."""
    city: str
    trip_days: int = Field(..., ge=1, le=10)
    categories: list[str] = []
    max_distance_per_day: int = Field(..., ge=1000)  # meters


class TravelConstraints(BaseModel):
    """Rota olusturma parametrelerini sinirlandiran sistem duzeyindeki planlama kisitlari."""
    max_trip_days: int = 10
    max_pois_per_day: int = 9
    max_daily_distance: int = 100_000  # meters
