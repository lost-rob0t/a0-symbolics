from __future__ import annotations

import os

import pytest

from plugins._prolog_rlm.helpers import credentials
from plugins._prolog_rlm.helpers.bridge import PrologRuntimeBridge


def test_resolve_prefers_settings_over_env(monkeypatch):
    monkeypatch.setattr(credentials, "_settings_credential", lambda: "settings-key")
    monkeypatch.setattr(credentials, "_framework_credential", lambda: "framework-key")
    monkeypatch.setenv(credentials.CREDENTIAL_ENV_NAME, "env-key")

    assert credentials.resolve_openrouter_credential() == "settings-key"

    monkeypatch.setattr(credentials, "_settings_credential", lambda: "")
    assert credentials.resolve_openrouter_credential() == "framework-key"

    monkeypatch.setattr(credentials, "_framework_credential", lambda: "")
    assert credentials.resolve_openrouter_credential() == "env-key"


def test_resolve_rejects_masked_and_empty_values(monkeypatch):
    monkeypatch.setattr(credentials, "_settings_credential", lambda: "************")
    monkeypatch.setattr(credentials, "_framework_credential", lambda: "None")
    monkeypatch.delenv(credentials.CREDENTIAL_ENV_NAME, raising=False)

    assert credentials.resolve_openrouter_credential() == ""

    monkeypatch.setenv(credentials.CREDENTIAL_ENV_NAME, "   ")
    assert credentials.resolve_openrouter_credential() == ""


def test_worker_environment_carries_credential_only(monkeypatch):
    monkeypatch.setattr(credentials, "resolve_openrouter_credential", lambda: "secret-key")
    env = credentials.worker_environment({"openrouter_model": "test-model"})
    assert env == {credentials.CREDENTIAL_ENV_NAME: "secret-key"}

    monkeypatch.setattr(credentials, "resolve_openrouter_credential", lambda: "")
    assert credentials.worker_environment() == {}


def test_bridge_injects_credential_into_worker_environment(monkeypatch):
    monkeypatch.setattr(credentials, "resolve_openrouter_credential", lambda: "secret-key")
    bridge = PrologRuntimeBridge({"openrouter_model": "test-model"})

    # Construction is lazy; the stored environment feeds the worker spawn.
    assert bridge.environment[credentials.CREDENTIAL_ENV_NAME] == "secret-key"
    assert bridge.environment["OPENROUTER_TEST_MODEL"] == "test-model"


def test_bridge_without_credential_keeps_model_only(monkeypatch):
    monkeypatch.setattr(credentials, "resolve_openrouter_credential", lambda: "")
    bridge = PrologRuntimeBridge({"openrouter_model": "test-model"})

    assert bridge.environment == {"OPENROUTER_TEST_MODEL": "test-model"}
