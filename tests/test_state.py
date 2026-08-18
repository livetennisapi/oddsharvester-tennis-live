from __future__ import annotations

from oddsharvester_tennis_live.state import (
    break_point_for,
    live_state,
    to_oddsharvester_live_record,
)


def test_break_point_receiver_at_ad():
    # server=1, receiver=2 at AD -> break point for player 2.
    score = {"server": 1, "points": ["40", "AD"], "is_tiebreak": False}
    assert break_point_for(score) == 2


def test_break_point_receiver_at_40_vs_server_lower():
    score = {"server": 2, "points": ["40", "30"], "is_tiebreak": False}
    # server=2 at 30, receiver=1 at 40 -> break point for player 1.
    assert break_point_for(score) == 1


def test_break_point_none_when_server_leads():
    score = {"server": 1, "points": ["40", "30"], "is_tiebreak": False}
    assert break_point_for(score) is None


def test_break_point_never_in_tiebreak():
    score = {"server": 1, "points": ["6", "7"], "is_tiebreak": True}
    assert break_point_for(score) is None


def test_break_point_none_when_points_null():
    assert break_point_for({"server": 1, "points": [None, None]}) is None
    assert break_point_for({"server": None, "points": ["40", "AD"]}) is None
    assert break_point_for(None) is None


def test_live_state_carries_source_and_no_odds(api_live_matches):
    block = live_state(api_live_matches[0], {"p1": "home", "p2": "away"})
    assert block["source"] == "livetennisapi.com"
    assert block["match_id"] == 900001
    assert block["server"] == 1
    assert block["serving_player"] == "Novak Djokovic"
    assert block["break_point_for"] == 2
    assert block["break_point_player"] == "Jiri Lehecka"
    # State only — nothing resembling odds/prices leaks in.
    joined = " ".join(str(k) for k in block).lower()
    assert "odd" not in joined
    assert "price" not in joined


def test_live_state_retired(api_live_matches):
    block = live_state(api_live_matches[1], {"p1": "away", "p2": "home"})
    assert block["event_status"] == "Retired"
    assert block["winner"] == 1
    assert block["withdrew"] == 2


def test_companion_record_shape(api_live_matches):
    rec = to_oddsharvester_live_record(api_live_matches[0], "2025-01-19T09:06:00Z")
    assert rec["data_source"] == "livetennisapi.com"
    assert rec["home_team"] == "Novak Djokovic"
    assert rec["away_team"] == "Jiri Lehecka"
    assert rec["live_score_home"] == 1
    assert rec["live_score_away"] == 0
    assert rec["live_score_raw"].startswith("1:0 (")
    assert rec["scraped_at_utc"] == "2025-01-19T09:06:00Z"
    # No odds keys of any kind.
    assert not any("odd" in k or "price" in k for k in rec)
