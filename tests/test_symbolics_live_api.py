from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest


LIVE_URL = os.getenv("A0_SYMBOLICS_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not LIVE_URL,
    reason="set A0_SYMBOLICS_URL to run the live Symbolics API test",
)


def _request(path: str):
    request = Request(
        f"{LIVE_URL.rstrip('/')}{path}",
        headers={"Accept": "application/json"},
    )
    try:
        return urlopen(request, timeout=10)
    except URLError as error:
        pytest.fail(f"Symbolics API is not reachable at {request.full_url}: {error}")


def test_live_symbolics_api_serves_ui_and_health_endpoint():
    with _request("/") as response:
        assert response.status == 200
        assert "text/html" in response.headers.get("Content-Type", "")

    with _request("/api/health") as response:
        assert response.status == 200
        assert "application/json" in response.headers.get("Content-Type", "")
        payload = json.loads(response.read().decode("utf-8"))

    assert isinstance(payload, dict)
    assert set(payload) >= {"gitinfo", "error"}
    assert payload["gitinfo"] is None or isinstance(payload["gitinfo"], dict)
    assert payload["error"] is None or isinstance(payload["error"], str)
