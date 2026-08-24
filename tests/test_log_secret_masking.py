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
