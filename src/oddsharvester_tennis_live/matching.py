"""Join OddsHarvester tennis rows to Live Tennis API matches by player + date.

Two different name shapes have to meet here:

* OddsHarvester tennis records carry the OddsPortal short form, surname first
  then an initial, e.g. ``"Djokovic N."`` / ``"De Minaur A."``.
* The Live Tennis API returns a full name, forename first, e.g.
  ``"Novak Djokovic"`` / ``"Alex De Minaur"``.

The safe common denominator is the *surname*. We reduce each name to its
lower-cased, accent-stripped surname tokens (dropping one-letter initials) and
require both participants of a match to line up, in either home/away ↔ p1/p2
orientation. A same-day (UTC) date guard disambiguates players who share a
surname but play on different days.

This is deliberately conservative: an ambiguous name (same surname, same day)
is reported as a non-match rather than guessed. Nothing is fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any
import unicodedata

_INITIAL_RE = re.compile(r"^[a-z]\.?$")
_TOKEN_SPLIT_RE = re.compile(r"[\s\-]+")


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_tokens(name: str) -> list[str]:
    """Lower-case, accent-strip and split a name into alphabetic tokens."""
    if not name:
        return []
    cleaned = _strip_accents(name).lower().replace(".", " ")
    tokens = [tok for tok in _TOKEN_SPLIT_RE.split(cleaned) if tok]
    return [tok for tok in tokens if tok.isalpha()]


def surname_tokens(name: str, *, surname_first: bool) -> list[str]:
    """Reduce a name to its surname tokens.

    ``surname_first`` picks the format:

    * ``True`` for OddsPortal/OddsHarvester ("Djokovic N.") — the surname is the
      leading run of multi-letter tokens, and the trailing initial is dropped.
    * ``False`` for the Live Tennis API ("Novak Djokovic") — the surname is the
      trailing run; a single leading forename token is dropped, and any
      lowercase particle ("de", "van", "der") is kept as part of the surname.
    """
    tokens = normalize_tokens(name)
    multi = [tok for tok in tokens if len(tok) > 1]
    if not multi:
        return []
    if surname_first:
        # Keep the leading run of full tokens (the surname), stop at the initial.
        surname: list[str] = []
        for tok in tokens:
            if _INITIAL_RE.match(tok):
                break
            surname.append(tok)
        return [tok for tok in surname if len(tok) > 1] or multi
    # Surname-last: drop exactly the first forename token when more than one
    # multi-letter token is present; particles stay attached to the surname.
    if len(multi) == 1:
        return multi
    return multi[1:]


def _surname_matches(oh_name: str, api_name: str) -> bool:
    oh = surname_tokens(oh_name, surname_first=True)
    api = surname_tokens(api_name, surname_first=False)
    if not oh or not api:
        return False
    api_set = set(api)
    # Every OddsHarvester surname token must be present on the API side.
    return all(tok in api_set for tok in oh)


@dataclass(frozen=True)
class MatchResult:
    """A resolved join between an OddsHarvester row and an API match."""

    api_match: dict[str, Any]
    # Maps API player key -> OddsHarvester side, e.g. {"p1": "home", "p2": "away"}.
    orientation: dict[str, str]


def _api_names(api_match: dict[str, Any]) -> tuple[str | None, str | None]:
    players = api_match.get("players") or {}
    p1 = (players.get("p1") or {}).get("name")
    p2 = (players.get("p2") or {}).get("name")
    return p1, p2


def _pair_orientation(home: str, away: str, p1: str | None, p2: str | None) -> dict[str, str] | None:
    if not p1 or not p2:
        return None
    if _surname_matches(home, p1) and _surname_matches(away, p2):
        return {"p1": "home", "p2": "away"}
    if _surname_matches(home, p2) and _surname_matches(away, p1):
        return {"p1": "away", "p2": "home"}
    return None


def _api_date(api_match: dict[str, Any]) -> date | None:
    raw = api_match.get("scheduled_time")
    if not raw:
        score = api_match.get("score") or {}
        raw = score.get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_oddsharvester_date(record: dict[str, Any]) -> date | None:
    """Parse the OddsHarvester ``match_date`` ("2025-01-19 08:15:00 UTC")."""
    raw = record.get("match_date") or record.get("date")
    if not raw:
        return None
    text = str(raw).strip().removesuffix(" UTC").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def find_match(
    record: dict[str, Any],
    api_matches: list[dict[str, Any]],
    *,
    date_tolerance_days: int = 1,
) -> MatchResult | None:
    """Find the single API match for an OddsHarvester row, or None.

    Returns None when there is no confident, unambiguous match: zero candidates,
    or more than one distinct candidate (a surname collision we refuse to guess).
    """
    home = record.get("home_team")
    away = record.get("away_team")
    if not home or not away:
        return None

    oh_date = parse_oddsharvester_date(record)
    candidates: list[MatchResult] = []
    for api_match in api_matches:
        p1, p2 = _api_names(api_match)
        orientation = _pair_orientation(home, away, p1, p2)
        if orientation is None:
            continue
        if oh_date is not None:
            api_day = _api_date(api_match)
            if api_day is not None and abs((api_day - oh_date).days) > date_tolerance_days:
                continue
        candidates.append(MatchResult(api_match=api_match, orientation=orientation))

    if len(candidates) != 1:
        # 0 = no match; >1 = ambiguous. Either way we do not guess.
        return None
    return candidates[0]
