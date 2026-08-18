"""Turn a Live Tennis API match into live STATE — never odds.

Everything in here is match state: score, serving side, break point, status.
No market price or model field is read or emitted. That is the whole point of
this package: OddsHarvester owns the OddsPortal odds; this is only the
live-state layer beside them, from a clearly separate source.
"""

from __future__ import annotations

from typing import Any

SOURCE = "livetennisapi.com"
PROVENANCE_NOTE = (
    "Live match STATE from the Live Tennis API, a separate source from OddsPortal. "
    "These are scores and status only, never market prices — do not treat them as "
    "OddsPortal odds or as interchangeable with OddsHarvester's scraped bookmaker data."
)

_POINT_ORDER = {"0", "15", "30"}


def break_point_for(score: dict[str, Any] | None) -> int | None:
    """Which player (1|2) holds a break point, or None.

    Definition (as the Live Tennis API derives it): the receiver is at AD, or the
    receiver is at 40 while the server is at 0/15/30. Never in a tiebreak, and
    never when the server or the points are null.
    """
    if not score:
        return None
    if score.get("is_tiebreak"):
        return None
    server = score.get("server")
    if server not in (1, 2):
        return None
    points = score.get("points")
    if not isinstance(points, list) or len(points) < 2:
        return None
    receiver = 2 if server == 1 else 1
    server_point = points[server - 1]
    receiver_point = points[receiver - 1]
    if server_point is None or receiver_point is None:
        return None
    if receiver_point == "AD":
        return receiver
    if receiver_point == "40" and server_point in _POINT_ORDER:
        return receiver
    return None


def _player_name(api_match: dict[str, Any], side: int) -> str | None:
    players = api_match.get("players") or {}
    return (players.get(f"p{side}") or {}).get("name")


def live_state(api_match: dict[str, Any], orientation: dict[str, str]) -> dict[str, Any]:
    """Compact, source-labelled live-state block for an enriched OddsHarvester row.

    Scores stay in the API's own p1/p2 order; ``orientation`` records which of
    OddsHarvester's home/away each maps to, so a consumer can align them without
    us silently reordering anything.
    """
    score = api_match.get("score") or None
    server = score.get("server") if score else None
    bp = break_point_for(score)
    return {
        "source": SOURCE,
        "note": PROVENANCE_NOTE,
        "match_id": api_match.get("id"),
        "matched_by": "player-surnames+date",
        "orientation": dict(orientation),
        "status": api_match.get("status"),
        "event_status": api_match.get("event_status"),
        "tour": api_match.get("tour"),
        "round": api_match.get("round"),
        "surface": api_match.get("surface"),
        "sets": (score or {}).get("sets"),
        "games": (score or {}).get("games"),
        "points": (score or {}).get("points"),
        "server": server,
        "serving_player": _player_name(api_match, server) if server in (1, 2) else None,
        "is_tiebreak": (score or {}).get("is_tiebreak"),
        "break_point_for": bp,
        "break_point_player": _player_name(api_match, bp) if bp in (1, 2) else None,
        "winner": api_match.get("winner"),
        "withdrew": api_match.get("withdrew"),
        "as_of": (score or {}).get("timestamp"),
    }


def _sets_won(score: dict[str, Any]) -> tuple[int | None, int | None]:
    """(sets_p1, sets_p2). Trusts a 2-element ``sets`` array; else counts sets
    won from the per-set ``games`` lists. Returns Nones when neither is usable."""
    sets = score.get("sets")
    if isinstance(sets, list) and len(sets) == 2 and all(isinstance(v, int) for v in sets):
        return sets[0], sets[1]
    games = score.get("games")
    if isinstance(games, list) and len(games) == 2:
        p1_sets = p2_sets = 0
        p1_list, p2_list = games[0] or [], games[1] or []
        for g1, g2 in zip(p1_list, p2_list, strict=False):
            if g1 > g2:
                p1_sets += 1
            elif g2 > g1:
                p2_sets += 1
        return p1_sets, p2_sets
    return None, None


def _live_score_raw(home_sets: int | None, away_sets: int | None, games: Any, home_is_p1: bool) -> str | None:
    """Best-effort compound score string, OddsPortal-live style:
    "sets_h:sets_a (set1_h:set1_a, set2_h:set2_a, ...)"."""
    if home_sets is None or away_sets is None:
        return None
    head = f"{home_sets}:{away_sets}"
    if not (isinstance(games, list) and len(games) == 2):
        return head
    p1_list, p2_list = games[0] or [], games[1] or []
    home_list, away_list = (p1_list, p2_list) if home_is_p1 else (p2_list, p1_list)
    partials = [f"{h}:{a}" for h, a in zip(home_list, away_list, strict=False)]
    return f"{head} ({', '.join(partials)})" if partials else head


def _derive_period(score: dict[str, Any] | None) -> str | None:
    if not score:
        return None
    if score.get("is_tiebreak"):
        return "Tiebreak"
    games = score.get("games")
    if isinstance(games, list) and len(games) == 2 and isinstance(games[0], list):
        current_set = max(len(games[0]), len(games[1]))
        if current_set >= 1:
            ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(current_set, f"{current_set}th")
            return f"{ordinal} Set"
    return None


def to_oddsharvester_live_record(api_match: dict[str, Any], scraped_at_utc: str) -> dict[str, Any]:
    """Emit a currently-live tennis match in OddsHarvester's live record shape.

    The metadata and live-context field NAMES mirror OddsHarvester's live output
    (``home_team``, ``away_team``, ``live_period``, ``live_score_home/away``,
    ``live_score_raw``, ``scraped_at_utc``) so the record slots into the same
    downstream processing. It carries NO market/odds keys, and every record is
    stamped ``data_source`` so its origin is never confused with an OddsPortal
    scrape. ``live_period`` is a derived label, not a copy of OddsPortal's text.
    """
    home = _player_name(api_match, 1)
    away = _player_name(api_match, 2)
    score = api_match.get("score") or None
    home_sets, away_sets = _sets_won(score) if score else (None, None)
    return {
        "data_source": SOURCE,
        "source_note": PROVENANCE_NOTE,
        "match_id": api_match.get("id"),
        "sport": "tennis",
        "tour": api_match.get("tour"),
        "league_name": api_match.get("tournament"),
        "round": api_match.get("round"),
        "surface": api_match.get("surface"),
        "home_team": home,
        "away_team": away,
        "match_date": api_match.get("scheduled_time"),
        "status": api_match.get("status"),
        "event_status": api_match.get("event_status"),
        "live_period": _derive_period(score),
        "live_score_home": home_sets,
        "live_score_away": away_sets,
        "live_score_raw": _live_score_raw(home_sets, away_sets, (score or {}).get("games"), home_is_p1=True),
        "server": (score or {}).get("server"),
        "break_point_for": break_point_for(score),
        "scraped_at_utc": scraped_at_utc,
    }
