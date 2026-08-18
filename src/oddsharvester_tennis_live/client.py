"""Minimal read-only client for the Live Tennis API (FREE-tier endpoints only).

Vendor note: this package is maintained by the Live Tennis API
(https://livetennisapi.com). Only the FREE-tier, current-state endpoints are
used here: ``GET /matches?status=live``, ``GET /matches?status=upcoming`` and
``GET /fixtures``. No historical, market-price or model endpoints are touched,
so a FREE key (https://livetennisapi.com/subscribe/free) is enough.

The HTTP layer is the standard library only (``urllib``) to keep the dependency
footprint tiny; ``requests`` is deliberately avoided.
"""

from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://api.livetennisapi.com/api/public/v1"
DEFAULT_TIMEOUT = 20.0


class LiveTennisError(RuntimeError):
    """Base error for anything the Live Tennis API returns that we cannot use."""


class AuthError(LiveTennisError):
    """The API key is missing, wrong, or not entitled (401/403)."""


class RateLimitError(LiveTennisError):
    """The FREE-tier quota or per-minute limit was hit (429).

    The FREE tier is 30 requests/minute and 100/day. That budget is fine for
    development, testing and light (~15-minute-cadence) enrichment; it is NOT
    enough for continuous fast polling of in-play matches. See the README.
    """


class LiveTennisClient:
    """Read-only client over the FREE-tier current-state endpoints."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        opener: Any | None = None,
    ) -> None:
        if not api_key:
            raise AuthError(
                "A Live Tennis API key is required. Get a free one (no card) at "
                "https://livetennisapi.com/subscribe/free"
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # `opener` is injected in tests so no real network call is ever made.
        self._opener = opener or urllib.request.build_opener()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = ""
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                query = "?" + urllib.parse.urlencode(clean)
        url = f"{self.base_url}{path}{query}"
        request = urllib.request.Request(  # noqa: S310 - fixed https base_url
            url,
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "oddsharvester-tennis-live/0.1.0 (+https://livetennisapi.com)",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            self._raise_for_status(exc)
        except urllib.error.URLError as exc:  # pragma: no cover - network-only
            raise LiveTennisError(f"Could not reach the Live Tennis API: {exc.reason}") from exc
        return json.loads(body)

    @staticmethod
    def _raise_for_status(exc: urllib.error.HTTPError) -> None:
        status = exc.code
        detail = ""
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = ""
        if status in (401, 403):
            raise AuthError(
                f"Live Tennis API rejected the key ({status}). This tool only needs FREE-tier "
                f"endpoints; check the key at https://livetennisapi.com/subscribe/free. {detail}".strip()
            )
        if status == 429:
            raise RateLimitError(
                "Live Tennis API rate limit hit (429). FREE tier is 30/min and 100/day — "
                "space out calls, or move continuous in-play polling to a paid tier. "
                f"{detail}".strip()
            )
        raise LiveTennisError(f"Live Tennis API error {status}: {detail}".strip())

    def live_matches(self, *, tour: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        """Matches currently in progress (FREE: ``GET /matches?status=live``)."""
        payload = self._get("/matches", {"status": "live", "tour": tour, "limit": limit})
        return list(payload.get("data", []))

    def upcoming_matches(self, *, tour: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        """Scheduled matches not yet started (FREE: ``GET /matches?status=upcoming``)."""
        payload = self._get("/matches", {"status": "upcoming", "tour": tour, "limit": limit})
        return list(payload.get("data", []))

    def fixtures(self, *, tour: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        """Upcoming scheduled fixtures, earliest first (FREE: ``GET /fixtures``)."""
        payload = self._get("/fixtures", {"tour": tour, "limit": limit})
        return list(payload.get("data", []))
