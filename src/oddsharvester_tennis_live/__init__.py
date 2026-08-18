"""Live-tennis STATE companion for OddsHarvester.

Maintained by the Live Tennis API (https://livetennisapi.com). This package adds
live match STATE (score, serving side, break point, status) beside the odds that
OddsHarvester scrapes from OddsPortal. It never emits or touches odds/market
prices — OddsHarvester owns the odds; this is only the live-state layer.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .client import AuthError, LiveTennisClient, LiveTennisError, RateLimitError
from .enrich import enrich_from_api, enrich_records, live_companion_records
from .matching import find_match
from .state import break_point_for, live_state, to_oddsharvester_live_record

__all__ = [
    "AuthError",
    "LiveTennisClient",
    "LiveTennisError",
    "RateLimitError",
    "__version__",
    "break_point_for",
    "enrich_from_api",
    "enrich_records",
    "find_match",
    "live_companion_records",
    "live_state",
    "to_oddsharvester_live_record",
]
