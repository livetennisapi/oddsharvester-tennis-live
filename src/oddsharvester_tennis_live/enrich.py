"""Orchestration: enrich OddsHarvester tennis rows, or emit companion records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .client import LiveTennisClient
from .matching import find_match
from .state import live_state, to_oddsharvester_live_record

ENRICH_KEY = "live_tennis_api"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def enrich_records(
    records: list[dict[str, Any]],
    api_matches: list[dict[str, Any]],
    *,
    date_tolerance_days: int = 1,
) -> dict[str, int]:
    """Attach a namespaced ``live_tennis_api`` state block to each row, in place.

    A row that resolves to exactly one live/upcoming API match gets the state
    block; a row that matches none (or ambiguously) gets an explicit
    ``{"matched": False}`` marker so the absence is visible, not silent. The
    row's own OddsPortal fields are never modified. Returns simple counts.
    """
    matched = 0
    for record in records:
        result = find_match(record, api_matches, date_tolerance_days=date_tolerance_days)
        if result is None:
            record[ENRICH_KEY] = {"matched": False, "source": "livetennisapi.com"}
            continue
        block = live_state(result.api_match, result.orientation)
        block["matched"] = True
        record[ENRICH_KEY] = block
        matched += 1
    return {"total": len(records), "matched": matched, "unmatched": len(records) - matched}


def enrich_from_api(
    records: list[dict[str, Any]],
    client: LiveTennisClient,
    *,
    tour: str | None = None,
    include_upcoming: bool = True,
    date_tolerance_days: int = 1,
) -> dict[str, int]:
    """Fetch current live (+ optionally upcoming) matches and enrich records."""
    api_matches = client.live_matches(tour=tour)
    if include_upcoming:
        api_matches = api_matches + client.upcoming_matches(tour=tour)
    return enrich_records(records, api_matches, date_tolerance_days=date_tolerance_days)


def live_companion_records(
    client: LiveTennisClient,
    *,
    tour: str | None = None,
) -> list[dict[str, Any]]:
    """Emit currently-live tennis matches as OddsHarvester-shaped live records."""
    scraped_at = _utc_now_iso()
    return [to_oddsharvester_live_record(match, scraped_at) for match in client.live_matches(tour=tour)]
