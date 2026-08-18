from __future__ import annotations

from typing import Any

from oddsharvester_tennis_live.enrich import (
    ENRICH_KEY,
    enrich_from_api,
    enrich_records,
    live_companion_records,
)


class FakeClient:
    """Stands in for LiveTennisClient — returns canned data, no network."""

    def __init__(self, live: list[dict[str, Any]], upcoming: list[dict[str, Any]] | None = None):
        self._live = live
        self._upcoming = upcoming or []

    def live_matches(self, *, tour: str | None = None, limit: int = 200):
        return self._live

    def upcoming_matches(self, *, tour: str | None = None, limit: int = 200):
        return self._upcoming


def test_enrich_records_adds_block_and_preserves_odds(oddsharvester_rows, api_live_matches):
    stats = enrich_records(oddsharvester_rows, api_live_matches)
    assert stats == {"total": 3, "matched": 2, "unmatched": 1}

    first = oddsharvester_rows[0]
    assert first[ENRICH_KEY]["matched"] is True
    assert first[ENRICH_KEY]["match_id"] == 900001
    # The row's own OddsPortal odds are untouched.
    assert first["odds"] == {"match_winner": {"home": 1.2, "away": 4.8}}


def test_enrich_unmatched_row_marked_explicitly(oddsharvester_rows, api_live_matches):
    enrich_records(oddsharvester_rows, api_live_matches)
    assert oddsharvester_rows[2][ENRICH_KEY] == {"matched": False, "source": "livetennisapi.com"}


def test_enrich_from_api_uses_client(oddsharvester_rows, api_live_matches):
    client = FakeClient(live=api_live_matches)
    stats = enrich_from_api(oddsharvester_rows, client, include_upcoming=False)
    assert stats["matched"] == 2


def test_live_companion_records(api_live_matches):
    client = FakeClient(live=api_live_matches)
    records = live_companion_records(client)
    assert len(records) == 2
    assert all(r["data_source"] == "livetennisapi.com" for r in records)
    assert all("scraped_at_utc" in r for r in records)
