from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def check_api_health(base_url: str) -> dict:
    url = f"{base_url.rstrip('/')}/api/health"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"API health returned HTTP {response.status}")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise RuntimeError(
                    f"API health returned unexpected content type: {content_type}"
                )
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as error:
        raise RuntimeError(f"API health request failed: {error}") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"API health response could not be read: {error}") from error

    if not isinstance(payload, dict) or not {"gitinfo", "error"} <= payload.keys():
        raise RuntimeError("API health response is missing gitinfo/error fields")
    if not (
        payload["gitinfo"] is None or isinstance(payload["gitinfo"], dict)
    ) or not (payload["error"] is None or isinstance(payload["error"], str)):
        raise RuntimeError("API health response has invalid gitinfo/error fields")
    return payload


def main() -> None:
    source_root = Path(sys.argv[1] if len(sys.argv) > 1 else "/a0").resolve()
    if not (source_root / "run_ui.py").is_file():
        raise SystemExit(f"Agent Zero source is unavailable: {source_root}")

    os.chdir(source_root)
    sys.path.insert(0, str(source_root))
    check_api_health(os.getenv("A0_SYMBOLICS_SMOKE_URL", "http://127.0.0.1:80"))

    from helpers import plugins
    from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridge

    required_plugins = {"_prolog_rlm"}
    enabled_plugins = set(plugins.get_enabled_plugins(None))
    missing_plugins = sorted(required_plugins - enabled_plugins)
    if missing_plugins:
        raise RuntimeError(
            "symbolic plugins are not enabled: " + ", ".join(missing_plugins)
        )

    compile_request = {
        "message": "Return a deterministic symbolic deployment status.",
        "max_context_tokens": 2048,
        "units": [
            {
                "format": "agent_zero_tool",
                "kind": "tool",
                "category": "agent",
                "name": "response",
                "description": "Return the final answer",
                "content": "### response",
                "schema": {"type": "object", "properties": {}},
                "effect": "read",
                "permanent": True,
            }
        ],
    }

    runtime = PrologRuntimeBridge({"request_timeout_seconds": 10.0})
    try:
        compiled = runtime.call("context_compile", {"request": compile_request})
        status = runtime.call("status")
    finally:
        runtime.close()

    if compiled["active_tools"] != ["response"]:
        raise RuntimeError("Prolog-RLM did not retain the permanent response tool")
    if status.get("ready") is not True or status.get("policy_owner") != "prolog":
        raise RuntimeError("Prolog-RLM did not report ready Prolog authority")

    print(
        json.dumps(
            {
                "active_tools": compiled["active_tools"],
                "fingerprint": compiled["fingerprint"],
                "integration_path": [
                    "agent-zero-plugin-registry",
                    "prolog-rlm-context-compile",
                    "prolog-rlm-model-turn",
                    "prolog-rlm",
                ],
                "policy_owner": status["policy_owner"],
                "ready": status["ready"],
                "runtime": status["runtime"],
                "version": status["version"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
