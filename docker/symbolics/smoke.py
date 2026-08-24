from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    source_root = Path(sys.argv[1] if len(sys.argv) > 1 else "/a0").resolve()
    if not (source_root / "run_ui.py").is_file():
        raise SystemExit(f"Agent Zero source is unavailable: {source_root}")

    os.chdir(source_root)
    sys.path.insert(0, str(source_root))

    from helpers import plugins
    from plugins._prolog_context_compiler.helpers.bridge import PrologContextBridge
    from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridge

    required_plugins = {"_prolog_context_compiler", "_prolog_rlm"}
    enabled_plugins = set(plugins.get_enabled_plugins(None))
    missing_plugins = sorted(required_plugins - enabled_plugins)
    if missing_plugins:
        raise RuntimeError(
            "symbolic plugins are not enabled: " + ", ".join(missing_plugins)
        )

    extension_paths = plugins.get_enabled_plugin_paths(
        None, "extensions", "python", "system_prompt"
    )
    if not any("_prolog_context_compiler" in path for path in extension_paths):
        raise RuntimeError("the Prolog context compiler extension is not discoverable")

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

    compiler = PrologContextBridge(timeout=10.0)
    runtime = PrologRuntimeBridge({"request_timeout_seconds": 10.0})
    try:
        compiled = compiler.compile(compile_request)
        status = runtime.call("status")
    finally:
        compiler.close()
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
                    "prolog-context-compiler",
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
