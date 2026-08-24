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
    RLM mode enables both as a single control plane. This function changes
    activation only; symbolic policy remains owned by Prolog-RLM.
    """

    from helpers import plugins

    selected_mode = resolve_mode(config)
    enable_rlm = selected_mode == MODE_RLM
    desired_state = "enabled" if enable_rlm else "disabled"

    metadata = {
        plugin_name: plugins.get_plugin_meta(plugin_name)
        for plugin_name in MANAGED_PLUGINS
    }
    missing = [name for name, meta in metadata.items() if meta is None]
    if enable_rlm and missing:
        raise RuntimeError(
            "Symbolics RLM mode requires bundled plugins: " + ", ".join(missing)
        )

    original_states = {
        plugin_name: plugins.get_toggle_state(plugin_name)
        for plugin_name, meta in metadata.items()
        if meta is not None
    }
    changed: list[str] = []

    try:
        for plugin_name, state in original_states.items():
            if state == desired_state:
                continue
            plugins.toggle_plugin(plugin_name, enable_rlm)
            changed.append(plugin_name)

        mismatched = [
            plugin_name
            for plugin_name in original_states
            if plugins.get_toggle_state(plugin_name) != desired_state
        ]
        if mismatched:
            raise RuntimeError(
                "Symbolics runtime mode transition did not converge for: "
                + ", ".join(mismatched)
            )
    except Exception:
        for plugin_name in reversed(changed):
            original_enabled = original_states[plugin_name] == "enabled"
            try:
                plugins.toggle_plugin(plugin_name, original_enabled)
            except Exception:
                pass
        raise

    return selected_mode
