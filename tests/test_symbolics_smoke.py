from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import URLError

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from docker.symbolics import smoke


class _Response:
    def __init__(self, status: int, content_type: str, body: bytes) -> None:
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_api_health_probe_validates_response_contract(monkeypatch) -> None:
    response = _Response(
        200,
        "application/json",
        json.dumps({"gitinfo": None, "error": None}).encode("utf-8"),
    )
    observed = {}

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["accept"] = request.get_header("Accept")
        observed["timeout"] = timeout
        return response

    monkeypatch.setattr(smoke, "urlopen", fake_urlopen)

    assert smoke.check_api_health("http://127.0.0.1:80/") == {
        "gitinfo": None,
        "error": None,
    }
    assert observed == {
        "url": "http://127.0.0.1:80/api/health",
        "accept": "application/json",
        "timeout": 5,
    }


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (_Response(503, "application/json", b"{}"), "HTTP 503"),
        (_Response(200, "text/plain", b"{}"), "content type"),
        (_Response(200, "application/json", b"not-json"), "could not be read"),
        (
            _Response(200, "application/json", b'{"gitinfo": null}'),
            "missing gitinfo/error",
        ),
        (
            _Response(
                200,
                "application/json",
                b'{"gitinfo": [], "error": null}',
            ),
            "invalid gitinfo/error",
        ),
    ],
)
def test_api_health_probe_rejects_invalid_responses(
    monkeypatch, response: _Response, message: str
) -> None:
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: response)

    with pytest.raises(RuntimeError, match=message):
        smoke.check_api_health("http://127.0.0.1:80")


def test_api_health_probe_rejects_unavailable_server(monkeypatch) -> None:
    def unavailable(*_args, **_kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(smoke, "urlopen", unavailable)

    with pytest.raises(RuntimeError, match="API health request failed"):
        smoke.check_api_health("http://127.0.0.1:80")
