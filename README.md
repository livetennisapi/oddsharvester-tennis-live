# oddsharvester-tennis-live

**Live-tennis _state_ companion for [OddsHarvester](https://github.com/jordantete/OddsHarvester).**

> **Who makes this.** This package is built and maintained by the **Live Tennis API**
> ([livetennisapi.com](https://livetennisapi.com)) — so it is vendor-authored;
> weigh it accordingly. It is an independent companion, **not** part of
> OddsHarvester and not affiliated with it. OddsHarvester is MIT-licensed and
> authored by Jordan Tete.

OddsHarvester scrapes historical, upcoming and live tennis odds from OddsPortal.
What it deliberately does **not** carry is a rich, low-latency picture of the
*match itself* — who is serving, the point score, whether it is break point,
whether a player retired. Its `live` command can get a live score, but only by
reloading OddsPortal through Playwright per sample (heavy, brittle on selector
changes, and the docs recommend keeping ≥60s between snapshots).

This package adds that missing layer: **live match state** — score by set,
game score, serving side, break-point flag, and status
(live / retired / walkover / interrupted / completed) — from the Live Tennis API,
joined onto OddsHarvester's own tennis rows by player surname and date.

## What it complements (and what it does not)

| Data | Owner | This package |
|------|-------|--------------|
| OddsPortal odds (per-bookmaker prices, market lines) | **OddsHarvester** | never touched, never emitted |
| Live match state (score, serving, break point, status) | **Live Tennis API** | added as a separate, labelled block |

**OddsHarvester owns the odds. This is only the live-state layer beside them.**

### On data provenance (deliberate design)

The two data sources are kept visibly separate on purpose:

- Enriched state is written under a single namespaced key, **`live_tennis_api`**,
  never merged into OddsHarvester's own fields. Your scraped odds rows are
  returned byte-for-byte unchanged, with one key added.
- Every state block carries `"source": "livetennisapi.com"` and a note stating
  it is match state from a separate source, **not** OddsPortal data.
- **No odds, prices or market fields are ever read or emitted by this tool.**
  Live scores and bookmaker odds are different things from different sources;
  this package will never make one look like the other.

## Install

```bash
pip install oddsharvester-tennis-live
```

Only one runtime dependency (`click`); the HTTP layer is the Python standard
library.

## Get a key

A **free** Live Tennis API key (no card) is enough — this tool only uses
free-tier, current-state endpoints:
[livetennisapi.com/subscribe/free](https://livetennisapi.com/subscribe/free).

```bash
export LIVE_TENNIS_API_KEY="your-free-key"
```

### Free-tier limits — read this before scripting

The free tier is **30 requests/minute and 100 requests/day**. Each `enrich` or
`live` run makes 1–2 API calls, so that budget is fine for development, testing
and **light (~15-minute-cadence) enrichment** — it is **not** enough for
continuous, fast in-play polling of many matches. If you sample in-play tennis
at high frequency, a paid tier lifts the limits; this tool works identically on
any tier. (`429` errors are reported plainly, never swallowed.)

## Usage

### 1. Enrich OddsHarvester tennis output

Run OddsHarvester as usual, then add live state to the tennis rows:

```bash
# OddsHarvester produces upcoming/live tennis rows (with its odds):
oddsharvester upcoming -s tennis -l atp-... -m match_winner -f json -o tennis.json --headless

# Add a live_tennis_api state block to each row:
oddsharvester-tennis-live enrich tennis.json -o tennis.enriched.json
```

Each matched row gains:

```json
{
  "home_team": "Djokovic N.",
  "away_team": "Lehecka J.",
  "odds": { "...": "your scraped OddsPortal odds, untouched" },
  "live_tennis_api": {
    "source": "livetennisapi.com",
    "note": "Live match STATE ... never market prices ...",
    "matched": true,
    "match_id": 900001,
    "orientation": { "p1": "home", "p2": "away" },
    "status": "live",
    "event_status": null,
    "sets": [1, 0],
    "games": [[6, 3], [3, 2]],
    "points": ["30", "40"],
    "server": 1,
    "serving_player": "Novak Djokovic",
    "break_point_for": 2,
    "break_point_player": "Jiri Lehecka",
    "as_of": "2025-01-19T09:05:00Z"
  }
}
```

Rows with no confident, unambiguous live/upcoming counterpart get
`{"matched": false}` — the absence is explicit, never a silent gap, and a
same-surname collision on the same day is reported as *unmatched* rather than
guessed. Scores stay in the API's own `p1`/`p2` order; `orientation` tells you
which maps to OddsHarvester's home/away.

Matching is best-effort on surname + date, so **confirm the players** for any
ambiguous name before relying on a join.

### 2. Companion live source (OddsHarvester-shaped records)

Emit currently-live tennis matches directly in OddsHarvester's live record
shape (`home_team`, `away_team`, `live_period`, `live_score_home/away`,
`live_score_raw`, `scraped_at_utc`) — no odds, and every record stamped
`data_source`:

```bash
oddsharvester-tennis-live live --tour atp -o live_state.json
```

`live_period` here is a derived label (e.g. `"2nd Set"`, `"Tiebreak"`), not a
copy of OddsPortal's exact text.

### As a library

```python
from oddsharvester_tennis_live import LiveTennisClient, enrich_from_api

client = LiveTennisClient("your-free-key")
records = [...]  # OddsHarvester tennis rows
stats = enrich_from_api(records, client)  # records mutated in place
print(stats)  # {"total": N, "matched": M, "unmatched": N-M}
```

## Break-point derivation

`break_point_for` is derived the way the Live Tennis API defines it: the
receiver is at **AD**, or the receiver is at **40** while the server is at
**0/15/30** — never in a tiebreak, and null whenever the server or points are
null.

## Scope, honestly

- **Live and upcoming tennis only.** Free-tier endpoints cover the current-state
  picture. Completed-match results and history are a paid product on the Live
  Tennis API, so this tool does not back-fill final results onto historic
  OddsHarvester rows.
- **Tennis only.**
- **We add state, never odds.** For odds, OddsHarvester is the source of truth.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q
```

All tests are offline (mocked HTTP + inline fixtures); none touch the network.

## License

MIT — see [LICENSE](LICENSE). OddsHarvester is a separate MIT project by its own
author; this package depends on nothing from it and merely reads and writes its
public JSON output shape.
