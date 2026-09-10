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


def _scoped_activation_conflicts(plugins: Any, desired_state: str) -> list[str]:
    """Return scoped toggles that could override the authoritative runtime mode."""

    desired_toggle = (
        plugins.ENABLED_FILE_NAME
        if desired_state == "enabled"
        else plugins.DISABLED_FILE_NAME
    )
    known_toggles = {plugins.ENABLED_FILE_NAME, plugins.DISABLED_FILE_NAME}
    conflicts: list[str] = []

    for plugin_name in MANAGED_PLUGINS:
        assets = plugins.find_plugin_assets(
            plugins.TOGGLE_FILE_PATTERN,
            plugin_name=plugin_name,
            project_name="*",
            agent_profile="*",
            only_first=False,
        )
        for asset in assets:
            project_name = str(asset.get("project_name") or "")
            agent_profile = str(asset.get("agent_profile") or "")
            if not (project_name or agent_profile):
                continue

            toggle_name = os.path.basename(str(asset.get("path") or ""))
            if toggle_name not in known_toggles or toggle_name == desired_toggle:
                continue

            scope = []
            if project_name:
                scope.append(f"project={project_name}")
            if agent_profile:
                scope.append(f"profile={agent_profile}")
            conflicts.append(
                f"{plugin_name} ({', '.join(scope)}): {toggle_name}"
            )

    return conflicts


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

    scoped_conflicts = _scoped_activation_conflicts(plugins, desired_state)
    if scoped_conflicts:
        raise RuntimeError(
            "Symbolics runtime mode has conflicting scoped activation override(s): "
            + "; ".join(scoped_conflicts)
            + ". Align or remove those scoped toggles before startup."
        )

    original_states = {
        plugin_name: plugins.get_toggle_state(plugin_name)
        for plugin_name, meta in metadata.items()
        if meta is not None
    }

    try:
        for plugin_name, state in original_states.items():
            if state == desired_state:
                continue
            plugins.toggle_plugin(plugin_name, enable_rlm)

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
    except Exception as transition_error:
        rollback_errors: list[str] = []
        for plugin_name in reversed(tuple(original_states)):
            original_state = original_states[plugin_name]
            try:
                if plugins.get_toggle_state(plugin_name) == original_state:
                    continue
                plugins.toggle_plugin(
                    plugin_name,
                    original_state == "enabled",
                )
            except Exception as rollback_error:
                rollback_errors.append(f"{plugin_name}: {rollback_error}")

        if rollback_errors:
            raise RuntimeError(
                "Symbolics runtime mode transition failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from transition_error
        raise

    return selected_mode
