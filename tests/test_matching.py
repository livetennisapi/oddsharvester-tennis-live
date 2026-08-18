from __future__ import annotations

from oddsharvester_tennis_live.matching import (
    find_match,
    normalize_tokens,
    parse_oddsharvester_date,
    surname_tokens,
)


def test_normalize_strips_accents_and_dots():
    assert normalize_tokens("N. Djoković") == ["n", "djokovic"]


def test_surname_first_drops_initial():
    assert surname_tokens("Djokovic N.", surname_first=True) == ["djokovic"]


def test_surname_first_multiword():
    assert surname_tokens("De Minaur A.", surname_first=True) == ["de", "minaur"]


def test_surname_last_drops_forename():
    assert surname_tokens("Novak Djokovic", surname_first=False) == ["djokovic"]


def test_surname_last_keeps_particles():
    assert surname_tokens("Alex De Minaur", surname_first=False) == ["de", "minaur"]


def test_parse_date_utc_suffix():
    date = parse_oddsharvester_date({"match_date": "2025-01-19 08:15:00 UTC"})
    assert date is not None
    assert date.isoformat() == "2025-01-19"


def test_find_match_same_orientation(oddsharvester_rows, api_live_matches):
    result = find_match(oddsharvester_rows[0], api_live_matches)
    assert result is not None
    assert result.api_match["id"] == 900001
    assert result.orientation == {"p1": "home", "p2": "away"}


def test_find_match_reversed_orientation(oddsharvester_rows, api_live_matches):
    result = find_match(oddsharvester_rows[1], api_live_matches)
    assert result is not None
    assert result.api_match["id"] == 900002
    # OddsHarvester home is "De Minaur" who is p2 on the API side.
    assert result.orientation == {"p1": "away", "p2": "home"}


def test_find_match_no_candidate(oddsharvester_rows, api_live_matches):
    assert find_match(oddsharvester_rows[2], api_live_matches) is None


def test_find_match_date_guard_rejects_wrong_day(api_live_matches):
    row = {
        "match_date": "2025-06-01 08:15:00 UTC",
        "home_team": "Djokovic N.",
        "away_team": "Lehecka J.",
    }
    assert find_match(row, api_live_matches, date_tolerance_days=1) is None


def test_find_match_ambiguous_returns_none():
    # Two live matches with the same surnames on the same day -> refuse to guess.
    row = {"match_date": "2025-01-19 08:15:00 UTC", "home_team": "Smith J.", "away_team": "Jones A."}
    twins = [
        {
            "id": i,
            "scheduled_time": "2025-01-19T08:15:00Z",
            "players": {"p1": {"name": "John Smith"}, "p2": {"name": "Alan Jones"}},
            "score": {},
        }
        for i in (1, 2)
    ]
    assert find_match(row, twins) is None
