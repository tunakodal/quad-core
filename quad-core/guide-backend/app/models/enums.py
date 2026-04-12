"""
Shared enumerations used across the GUIDE domain.
"""
from enum import Enum


class Language(str, Enum):
    """Supported language options for content and audio selection."""
    TR = "TR"
    EN = "EN"
    DE = "DE"


class RoutingProfile(str, Enum):
    """Routing mode used by the OSRM engine. The project only supports driving mode"""
    DRIVING = "driving"
