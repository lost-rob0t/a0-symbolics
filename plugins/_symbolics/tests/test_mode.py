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


def test_sync_rolls_back_partial_transition(monkeypatch):
    states, calls = _fake_activation(
        monkeypatch,
        "disabled",
        fail_on=("_prolog_context_compiler", True),
    )

    with pytest.raises(RuntimeError, match="synthetic toggle failure"):
        mode.sync_runtime_mode({"mode": "rlm"})

    assert states == {
        "_prolog_rlm": "disabled",
        "_prolog_context_compiler": "disabled",
    }
    assert calls == [
        ("_prolog_rlm", True),
        ("_prolog_context_compiler", True),
        ("_prolog_rlm", False),
    ]


def _fake_activation(monkeypatch, initial_state, fail_on=None):
    from helpers import plugins

    monkeypatch.delenv("A0_SYMBOLICS_MODE", raising=False)
    states = {name: initial_state for name in mode.MANAGED_PLUGINS}
    calls = []

    monkeypatch.setattr(plugins, "get_plugin_meta", lambda _name: object())
    monkeypatch.setattr(plugins, "get_toggle_state", lambda name: states[name])

    def toggle(name, enabled):
        calls.append((name, enabled))
        if fail_on == (name, enabled):
            raise RuntimeError("synthetic toggle failure")
        states[name] = "enabled" if enabled else "disabled"

    monkeypatch.setattr(plugins, "toggle_plugin", toggle)
    return states, calls
