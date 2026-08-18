"""Shared fixtures — all data is inline; no network is ever touched."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def oddsharvester_rows() -> list[dict[str, Any]]:
    """OddsHarvester tennis records in the real output shape (surname-first names)."""
    return [
        {
            "match_date": "2025-01-19 08:15:00 UTC",
            "home_team": "Djokovic N.",
            "away_team": "Lehecka J.",
            "league_name": "australian-open",
            "match_link": "https://www.oddsportal.com/tennis/australia/atp-australian-open/djokovic-novak-lehecka-jiri-0ShOHpqe/",
            "odds": {"match_winner": {"home": 1.2, "away": 4.8}},
        },
        {
            "match_date": "2025-01-19 10:00:00 UTC",
            "home_team": "De Minaur A.",
            "away_team": "Sinner J.",
            "league_name": "australian-open",
            "match_link": "https://www.oddsportal.com/tennis/australia/atp-australian-open/de-minaur-alex-sinner-jannik-abc123/",
        },
        {
            "match_date": "2025-01-19 12:00:00 UTC",
            "home_team": "Nobody X.",
            "away_team": "Unknown Y.",
            "league_name": "australian-open",
        },
    ]


@pytest.fixture
def api_live_matches() -> list[dict[str, Any]]:
    """Live Tennis API match objects (full names, p1/p2, score block)."""
    return [
        {
            "id": 900001,
            "tournament": "Australian Open",
            "tour": "atp",
            "surface": "hard",
            "round": "R16",
            "status": "live",
            "event_status": None,
            "scheduled_time": "2025-01-19T08:15:00Z",
            "players": {
                "p1": {"id": 1, "name": "Novak Djokovic"},
                "p2": {"id": 2, "name": "Jiri Lehecka"},
            },
            "score": {
                "sets": [1, 0],
                "games": [[6, 3], [3, 2]],
                "points": ["30", "40"],
                "server": 1,
                "is_tiebreak": False,
                "timestamp": "2025-01-19T09:05:00Z",
            },
            "winner": None,
            "withdrew": None,
        },
        {
            # Names in reversed home/away orientation vs the OddsHarvester row.
            "id": 900002,
            "tournament": "Australian Open",
            "tour": "atp",
            "surface": "hard",
            "round": "R16",
            "status": "live",
            "event_status": "Retired",
            "scheduled_time": "2025-01-19T10:00:00Z",
            "players": {
                "p1": {"id": 3, "name": "Jannik Sinner"},
                "p2": {"id": 4, "name": "Alex De Minaur"},
            },
            "score": {
                "sets": [2, 0],
                "games": [[6, 6], [4, 2]],
                "points": ["40", "AD"],
                "server": 1,
                "is_tiebreak": False,
                "timestamp": "2025-01-19T11:30:00Z",
            },
            "winner": 1,
            "withdrew": 2,
        },
    ]
