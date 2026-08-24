from __future__ import annotations

import os
from typing import Any


MODE_NATIVE = "native"
MODE_RLM = "rlm"
VALID_MODES = frozenset({MODE_NATIVE, MODE_RLM})
MANAGED_PLUGINS = ("_prolog_rlm", "_prolog_context_compiler")


def resolve_mode(config: dict[str, Any] | None = None) -> str:
    """Resolve the one authoritative Symbolics runtime mode."""

    if config is None:
        from helpers import plugins

        config = plugins.get_plugin_config("_symbolics") or {}

    raw = os.getenv("A0_SYMBOLICS_MODE") or (config or {}).get("mode") or MODE_NATIVE
    mode = str(raw).strip().lower()
    if mode not in VALID_MODES:
        allowed = ", ".join(sorted(VALID_MODES))
        raise RuntimeError(
            f"Invalid Symbolics runtime mode {raw!r}; expected one of: {allowed}"
        )
    return mode


def sync_runtime_mode(config: dict[str, Any] | None = None) -> str:
    """Synchronize the paired RLM plugins to the selected runtime mode.

    Native mode removes both plugins from Agent Zero's active plugin set.
    RLM mode enables both as a single control plane.  This function changes
    activation only; symbolic policy remains owned by Prolog-RLM.
    """

    from helpers import plugins

    mode = resolve_mode(config)
    enable_rlm = mode == MODE_RLM
    desired_state = "enabled" if enable_rlm else "disabled"

    missing: list[str] = []
    for plugin_name in MANAGED_PLUGINS:
        if plugins.get_plugin_meta(plugin_name) is None:
            missing.append(plugin_name)
            continue
        if plugins.get_toggle_state(plugin_name) != desired_state:
            plugins.toggle_plugin(plugin_name, enable_rlm)

    if enable_rlm and missing:
        raise RuntimeError(
            "Symbolics RLM mode requires bundled plugins: " + ", ".join(missing)
        )

    return mode
