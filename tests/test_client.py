from __future__ import annotations

import io
import json
import urllib.error

import pytest

from oddsharvester_tennis_live.client import (
    AuthError,
    LiveTennisClient,
    LiveTennisError,
    RateLimitError,
)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class FakeOpener:
    """Captures the outbound request and returns a canned body or raises."""

    def __init__(self, *, body=None, error=None):
        self._body = body
        self._error = error
        self.last_request = None

    def open(self, request, timeout=None):
        self.last_request = request
        if self._error is not None:
            raise self._error
        return FakeResponse(json.dumps(self._body).encode("utf-8"))


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b'{"error":"x"}'))


def test_requires_key():
    with pytest.raises(AuthError):
        LiveTennisClient("")


def test_live_matches_sends_key_and_parses(api_live_matches):
    opener = FakeOpener(body={"data": api_live_matches})
    client = LiveTennisClient("free-key", opener=opener)
    out = client.live_matches(tour="atp")
    assert len(out) == 2
    # urllib stores header keys capitalized: "X-API-Key" -> "X-api-key".
    assert opener.last_request.get_header("X-api-key") == "free-key"
    assert "status=live" in opener.last_request.full_url
    assert "tour=atp" in opener.last_request.full_url


def test_fixtures_endpoint(api_live_matches):
    opener = FakeOpener(body={"data": []})
    client = LiveTennisClient("free-key", opener=opener)
    assert client.fixtures() == []
    assert opener.last_request.full_url.endswith("/fixtures?limit=200")


def test_auth_error_maps_403():
    client = LiveTennisClient("bad", opener=FakeOpener(error=_http_error(403)))
    with pytest.raises(AuthError):
        client.live_matches()


def test_rate_limit_maps_429():
    client = LiveTennisClient("free-key", opener=FakeOpener(error=_http_error(429)))
    with pytest.raises(RateLimitError):
        client.live_matches()


def test_generic_error_maps_500():
    client = LiveTennisClient("free-key", opener=FakeOpener(error=_http_error(500)))
    with pytest.raises(LiveTennisError):
        client.live_matches()
