"""
Backward-compatible re-export module.

All domain classes have been moved to focused submodules:
  - app.models.enums   → Language, RoutingProfile
  - app.models.geo     → GeoPoint
  - app.models.media   → MediaAsset
  - app.models.poi     → Poi, PoiContent
  - app.models.route   → RouteSegment, DayPlan, Itinerary, RoutePlan

New code should import directly from those submodules.
This file exists only to avoid breaking existing imports (e.g. tests).
"""
from app.models.enums import Language, RoutingProfile
from app.models.geo import GeoPoint
from app.models.media import MediaAsset
from app.models.poi import Poi, PoiContent
from app.models.route import RouteSegment, DayPlan, Itinerary, RoutePlan

__all__ = [
    "Language", "RoutingProfile",
    "GeoPoint",
    "MediaAsset",
    "Poi", "PoiContent",
    "RouteSegment", "DayPlan", "Itinerary", "RoutePlan",
]
