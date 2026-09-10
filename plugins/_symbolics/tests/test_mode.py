from __future__ import annotations

import pytest

from plugins._symbolics.helpers import mode


def test_resolve_mode_uses_config(monkeypatch):
    monkeypatch.delenv("A0_SYMBOLICS_MODE", raising=False)
    assert mode.resolve_mode({"mode": "native"}) == "native"
    assert mode.resolve_mode({"mode": "RLM"}) == "rlm"


def test_resolve_mode_environment_wins(monkeypatch):
    monkeypatch.setenv("A0_SYMBOLICS_MODE", "rlm")
    assert mode.resolve_mode({"mode": "native"}) == "rlm"


def test_resolve_mode_rejects_unknown_mode(monkeypatch):
    monkeypatch.delenv("A0_SYMBOLICS_MODE", raising=False)
    with pytest.raises(RuntimeError, match="Invalid Symbolics runtime mode"):
        mode.resolve_mode({"mode": "hybrid"})


def test_sync_native_disables_both_plugins(monkeypatch):
    states, calls = _fake_activation(monkeypatch, "enabled")

    assert mode.sync_runtime_mode({"mode": "native"}) == "native"
    assert states == {
        "_prolog_rlm": "disabled",
        "_prolog_context_compiler": "disabled",
    }
    assert calls == [
        ("_prolog_rlm", False),
        ("_prolog_context_compiler", False),
    ]


def test_sync_rlm_enables_both_plugins(monkeypatch):
    states, calls = _fake_activation(monkeypatch, "disabled")

    assert mode.sync_runtime_mode({"mode": "rlm"}) == "rlm"
    assert states == {
        "_prolog_rlm": "enabled",
        "_prolog_context_compiler": "enabled",
    }
    assert calls == [
        ("_prolog_rlm", True),
        ("_prolog_context_compiler", True),
    ]


def test_sync_rlm_fails_before_mutation_when_plugin_is_missing(monkeypatch):
    from helpers import plugins

    monkeypatch.delenv("A0_SYMBOLICS_MODE", raising=False)
    monkeypatch.setattr(
        plugins,
        "get_plugin_meta",
        lambda name: None if name == "_prolog_context_compiler" else object(),
    )
    calls = []
    monkeypatch.setattr(
        plugins,
        "toggle_plugin",
        lambda name, enabled: calls.append((name, enabled)),
    )

    with pytest.raises(RuntimeError, match="_prolog_context_compiler"):
        mode.sync_runtime_mode({"mode": "rlm"})
    assert calls == []


@pytest.mark.parametrize(
    ("selected_mode", "initial_state", "toggle_file"),
    [
        ("rlm", "disabled", ".toggle-0"),
        ("native", "enabled", ".toggle-1"),
    ],
)
def test_sync_fails_closed_on_conflicting_scoped_activation_override(
    monkeypatch,
    selected_mode,
    initial_state,
    toggle_file,
):
    from helpers import plugins

    states, calls = _fake_activation(monkeypatch, initial_state)

    def find_assets(*_subpaths, plugin_name="*", **_kwargs):
        if plugin_name != "_prolog_rlm":
            return []
        return [
            {
                "project_name": "project-a",
                "agent_profile": "",
                "path": f"/tmp/project-a/plugins/_prolog_rlm/{toggle_file}",
            }
        ]

    monkeypatch.setattr(plugins, "find_plugin_assets", find_assets)

    with pytest.raises(RuntimeError, match="conflicting scoped activation override"):
        mode.sync_runtime_mode({"mode": selected_mode})

    assert calls == []
    assert states == {name: initial_state for name in mode.MANAGED_PLUGINS}


def test_sync_rolls_back_partial_transition_even_if_toggle_raises_after_write(monkeypatch):
    states, calls = _fake_activation(
        monkeypatch,
        "disabled",
        fail_after_write=("_prolog_context_compiler", True),
    )

    with pytest.raises(RuntimeError, match="synthetic post-write toggle failure"):
        mode.sync_runtime_mode({"mode": "rlm"})

    assert states == {
        "_prolog_rlm": "disabled",
        "_prolog_context_compiler": "disabled",
    }
    assert calls == [
        ("_prolog_rlm", True),
        ("_prolog_context_compiler", True),
        ("_prolog_context_compiler", False),
        ("_prolog_rlm", False),
    ]


def _fake_activation(monkeypatch, initial_state, fail_after_write=None):
    from helpers import plugins

    monkeypatch.delenv("A0_SYMBOLICS_MODE", raising=False)
    states = {name: initial_state for name in mode.MANAGED_PLUGINS}
    calls = []

    monkeypatch.setattr(plugins, "get_plugin_meta", lambda _name: object())
    monkeypatch.setattr(plugins, "get_toggle_state", lambda name: states[name])

    def toggle(name, enabled):
        calls.append((name, enabled))
        states[name] = "enabled" if enabled else "disabled"
        if fail_after_write == (name, enabled):
            raise RuntimeError("synthetic post-write toggle failure")

    monkeypatch.setattr(plugins, "toggle_plugin", toggle)
    return states, calls
