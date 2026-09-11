"""Runtime-worker credential resolution for Prolog-RLM.

The Prolog-RLM runtime resolves its provider credential from the worker
process environment (``OPENROUTER_API_KEY``). Agent Zero stores the key in
settings, so this module resolves it from the framework's own configuration
sources and hands it to the bridge for process-env injection only.

The credential never appears in worker requests, results, logs, or repository
files; it exists solely inside the worker process environment, which shares
the framework process's trust domain.
"""

from __future__ import annotations

import os

CREDENTIAL_ENV_NAME = "OPENROUTER_API_KEY"
_SETTING_KEY = "openrouter"
_MASKED_VALUES = {"************", "None", ""}


def _settings_credential() -> str:
    try:
        from helpers import settings

        api_keys = (settings.get_settings() or {}).get("api_keys") or {}
        return str(api_keys.get(_SETTING_KEY) or "").strip()
    except Exception:
        return ""


def _framework_credential() -> str:
    try:
        from models import get_api_key

        return str(get_api_key(_SETTING_KEY) or "").strip()
    except Exception:
        return ""


def resolve_openrouter_credential() -> str:
    """Resolve the OpenRouter credential for the runtime worker env.

    Resolution order: Agent Zero settings ``api_keys["openrouter"]``, then the
    framework's dotenv resolver (``API_KEY_OPENROUTER``/``OPENROUTER_API_KEY``
    /``OPENROUTER_API_TOKEN``), then the ambient ``OPENROUTER_API_KEY``.
    Masked placeholders and empty values are rejected.
    """
    for candidate in (
        _settings_credential(),
        _framework_credential(),
        os.getenv(CREDENTIAL_ENV_NAME, "").strip(),
    ):
        if candidate and candidate not in _MASKED_VALUES:
            return candidate
    return ""


def worker_environment(config: dict | None = None) -> dict[str, str]:
    """Extra environment entries for the runtime worker process.

    Returns the bridge's credential injection: an empty dict when no
    credential can be resolved (the runtime reports its own typed fault).
    """
    key = resolve_openrouter_credential()
    return {CREDENTIAL_ENV_NAME: key} if key else {}
