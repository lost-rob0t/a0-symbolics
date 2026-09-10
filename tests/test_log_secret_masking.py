from __future__ import annotations

import helpers.log as log_module
from helpers.log import Log


SECRET = "sk-test-super-secret"


def test_secret_manager_lookup_failure_never_returns_original_string(monkeypatch):
    def fail_lookup(_context):
        raise RuntimeError("synthetic secret manager failure")

    monkeypatch.setattr(log_module, "get_secrets_manager", fail_lookup)

    masked = Log()._mask_recursive(SECRET)

    assert masked != SECRET
    assert SECRET not in str(masked)


def test_secret_manager_lookup_failure_never_leaks_secret_dict_key(monkeypatch):
    def fail_lookup(_context):
        raise RuntimeError("synthetic secret manager failure")

    monkeypatch.setattr(log_module, "get_secrets_manager", fail_lookup)

    masked = Log()._mask_recursive({SECRET: "ordinary value"})

    assert SECRET not in str(masked)


def test_mask_values_failure_never_returns_original_nested_secret(monkeypatch):
    class BrokenSecretsManager:
        def mask_values(self, _value):
            raise RuntimeError("synthetic masking failure")

    monkeypatch.setattr(
        log_module,
        "get_secrets_manager",
        lambda _context: BrokenSecretsManager(),
    )

    payload = {
        "safe": "ordinary value",
        "nested": [SECRET, {"token": SECRET}],
    }
    masked = Log()._mask_recursive(payload)

    assert SECRET not in str(masked)


def test_mask_values_failure_never_leaks_secret_dict_key(monkeypatch):
    class BrokenSecretsManager:
        def mask_values(self, _value):
            raise RuntimeError("synthetic masking failure")

    monkeypatch.setattr(
        log_module,
        "get_secrets_manager",
        lambda _context: BrokenSecretsManager(),
    )

    masked = Log()._mask_recursive({SECRET: "ordinary value"})

    assert SECRET not in str(masked)


def test_leaf_masking_failure_redacts_only_failed_leaf(monkeypatch):
    class SelectivelyBrokenSecretsManager:
        def mask_values(self, value):
            if value == SECRET:
                raise RuntimeError("synthetic masking failure")
            return value

    monkeypatch.setattr(
        log_module,
        "get_secrets_manager",
        lambda _context: SelectivelyBrokenSecretsManager(),
    )

    payload = {
        "safe": "ordinary value",
        "nested": [SECRET, {"safe": "still ordinary"}],
    }
    masked = Log()._mask_recursive(payload)

    assert masked["safe"] == "ordinary value"
    assert masked["nested"][1]["safe"] == "still ordinary"
    assert masked["nested"][0] != SECRET
    assert SECRET not in str(masked)


def test_log_item_output_never_contains_secret_when_masking_fails(monkeypatch):
    class BrokenSecretsManager:
        def mask_values(self, _value):
            raise RuntimeError("synthetic masking failure")

    monkeypatch.setattr(
        log_module,
        "get_secrets_manager",
        lambda _context: BrokenSecretsManager(),
    )

    item = Log().log(
        "info",
        heading=f"heading {SECRET}",
        content=f"content {SECRET}",
        kvps={"token": SECRET},
    )

    assert SECRET not in str(item.output())


def test_progress_never_contains_secret_when_masking_fails(monkeypatch):
    class BrokenSecretsManager:
        def mask_values(self, _value):
            raise RuntimeError("synthetic masking failure")

    monkeypatch.setattr(
        log_module,
        "get_secrets_manager",
        lambda _context: BrokenSecretsManager(),
    )

    log = Log()
    log.set_progress(f"progress {SECRET}")

    assert SECRET not in log.progress
