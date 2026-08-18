"""Command-line interface.

Two subcommands:

* ``enrich`` — read an OddsHarvester tennis JSON file, join each row to the
  current live/upcoming picture from the Live Tennis API, and write the same
  rows back with an added ``live_tennis_api`` state block.
* ``live`` — emit currently-live tennis matches as OddsHarvester-shaped live
  records (a companion live-state source, no odds).

The API key comes from ``--api-key`` or the ``LIVE_TENNIS_API_KEY`` environment
variable. A FREE key is enough: https://livetennisapi.com/subscribe/free
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import click

from . import __version__
from .client import DEFAULT_BASE_URL, LiveTennisClient, LiveTennisError
from .enrich import enrich_from_api, live_companion_records

ENV_KEY = "LIVE_TENNIS_API_KEY"


def _resolve_key(api_key: str | None) -> str:
    key = api_key or os.environ.get(ENV_KEY, "")
    if not key:
        raise click.ClickException(
            f"No API key. Pass --api-key or set {ENV_KEY}. "
            "Get a free key (no card) at https://livetennisapi.com/subscribe/free"
        )
    return key


def _load_records(path: str) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        # Tolerate a wrapped {"data": [...]} shape as well as a bare list.
        data = data.get("data", data.get("records", []))
    if not isinstance(data, list):
        raise click.ClickException(f"Expected a JSON array of match records in {path}.")
    return data


def _write(path: str | None, payload: Any) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        click.echo(text)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="oddsharvester-tennis-live")
def main() -> None:
    """Live-tennis STATE companion for OddsHarvester (vendor: Live Tennis API)."""


_key_option = click.option("--api-key", default=None, help=f"Live Tennis API key (or set {ENV_KEY}).")
_tour_option = click.option(
    "--tour",
    default=None,
    type=click.Choice(["atp", "wta", "challenger", "itf", "juniors"]),
    help="Restrict to one tour.",
)
_base_option = click.option("--base-url", default=DEFAULT_BASE_URL, help="Override the API base URL.")


@main.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", "output_file", default=None, help="Write here (default: stdout).")
@click.option("--no-upcoming", is_flag=True, help="Match only currently-live matches, not upcoming.")
@click.option("--date-tolerance", default=1, show_default=True, help="Allowed |days| between row and match.")
@_tour_option
@_key_option
@_base_option
def enrich(
    input_file: str,
    output_file: str | None,
    no_upcoming: bool,
    date_tolerance: int,
    tour: str | None,
    api_key: str | None,
    base_url: str,
) -> None:
    """Add a live_tennis_api state block to each OddsHarvester tennis row."""
    records = _load_records(input_file)
    client = LiveTennisClient(_resolve_key(api_key), base_url=base_url)
    try:
        stats = enrich_from_api(
            records,
            client,
            tour=tour,
            include_upcoming=not no_upcoming,
            date_tolerance_days=date_tolerance,
        )
    except LiveTennisError as exc:
        raise click.ClickException(str(exc)) from exc
    _write(output_file, records)
    click.echo(
        f"enriched {stats['matched']}/{stats['total']} rows ({stats['unmatched']} unmatched)",
        err=True,
    )


@main.command()
@click.option("-o", "--output", "output_file", default=None, help="Write here (default: stdout).")
@_tour_option
@_key_option
@_base_option
def live(output_file: str | None, tour: str | None, api_key: str | None, base_url: str) -> None:
    """Emit currently-live tennis as OddsHarvester-shaped live records (no odds)."""
    client = LiveTennisClient(_resolve_key(api_key), base_url=base_url)
    try:
        records = live_companion_records(client, tour=tour)
    except LiveTennisError as exc:
        raise click.ClickException(str(exc)) from exc
    if not records:
        click.echo("no live tennis matches right now", err=True)
        return
    _write(output_file, records)
    click.echo(f"emitted {len(records)} live record(s)", err=True)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
