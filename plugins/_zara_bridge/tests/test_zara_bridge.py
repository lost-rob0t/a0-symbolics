from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from plugins._zara_bridge.helpers.client import (
    ZaraBridgeConfig,
    ZaraBridgeError,
    ZaraDaemonClient,
)


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def fake_zara(directory: str, body: str) -> str:
    path = Path(directory) / "zara"
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return str(path)


def test_plugin_is_bundled_disabled_by_default():
    assert (PLUGIN_ROOT / ".toggle-0").is_file()
    manifest = (PLUGIN_ROOT / "plugin.yaml").read_text(encoding="utf-8")
    assert "name: _zara_bridge" in manifest
    assert "always_enabled: false" in manifest


def test_bridge_uses_existing_connect_cli_and_preserves_message():
    with tempfile.TemporaryDirectory() as directory:
        binary = fake_zara(
            directory,
            "import sys\n"
            "assert sys.argv[1] == '--connect'\n"
            "sys.stdout.write(sys.argv[2] + '|' + sys.argv[3])\n",
        )
        config = ZaraBridgeConfig.load(
            {
                "zara_binary": binary,
                "endpoint": "ipc:///tmp/zara.sock",
                "timeout_seconds": 2,
            }
        )
        result = ZaraDaemonClient(config).send("keep spaces intact")
    assert result == "ipc:///tmp/zara.sock|keep spaces intact"


def test_environment_can_supply_binary_and_endpoint(monkeypatch):
    monkeypatch.setenv("A0_ZARA_BINARY", "/tmp/custom-zara")
    monkeypatch.setenv("A0_ZARA_ENDPOINT", "tcp://127.0.0.1:5555")
    config = ZaraBridgeConfig.load({})
    assert config.zara_binary == "/tmp/custom-zara"
    assert config.endpoint == "tcp://127.0.0.1:5555"


def test_missing_endpoint_fails_before_process_start():
    config = ZaraBridgeConfig.load({"zara_binary": sys.executable})
    with pytest.raises(ZaraBridgeError, match="endpoint is not configured"):
        ZaraDaemonClient(config).send("hello")


def test_timeout_is_bounded():
    with tempfile.TemporaryDirectory() as directory:
        binary = fake_zara(
            directory,
            "import time\ntime.sleep(1)\n",
        )
        config = ZaraBridgeConfig.load(
            {
                "zara_binary": binary,
                "endpoint": "ipc:///tmp/zara.sock",
                "timeout_seconds": 0.1,
            }
        )
        with pytest.raises(ZaraBridgeError, match="exceeded 0.10s timeout"):
            ZaraDaemonClient(config).send("hello")


def test_nonzero_exit_returns_bounded_error():
    with tempfile.TemporaryDirectory() as directory:
        binary = fake_zara(
            directory,
            "import sys\nsys.stderr.write('daemon unavailable')\nsys.exit(7)\n",
        )
        config = ZaraBridgeConfig.load(
            {"zara_binary": binary, "endpoint": "ipc:///tmp/zara.sock"}
        )
        with pytest.raises(ZaraBridgeError, match="status 7: daemon unavailable"):
            ZaraDaemonClient(config).send("hello")


def test_output_limit_is_enforced():
    with tempfile.TemporaryDirectory() as directory:
        binary = fake_zara(
            directory,
            "import sys\nsys.stdout.write('x' * 100)\n",
        )
        config = ZaraBridgeConfig.load(
            {
                "zara_binary": binary,
                "endpoint": "ipc:///tmp/zara.sock",
                "max_output_chars": 10,
            }
        )
        with pytest.raises(ZaraBridgeError, match="response exceeded"):
            ZaraDaemonClient(config).send("hello")


def test_message_limit_is_enforced():
    config = ZaraBridgeConfig.load(
        {
            "zara_binary": sys.executable,
            "endpoint": "ipc:///tmp/zara.sock",
            "max_message_chars": 4,
        }
    )
    with pytest.raises(ZaraBridgeError, match="message exceeds"):
        ZaraDaemonClient(config).send("12345")
