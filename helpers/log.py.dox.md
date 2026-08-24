# log.py DOX

## Purpose

- Own the `log.py` helper module.
- This module owns chat log items, outputs, truncation, secret masking, and dirty-state integration.
- Keep this file-level DOX profile synchronized with `log.py` because this directory is intentionally flat.

## Ownership

- `log.py` owns the runtime implementation.
- `log.py.dox.md` owns durable notes about responsibilities, contracts, side effects, and verification for that implementation.
- Classes:
- `LogItem` (no explicit base class)
  - `update(self, type: Type | None=..., heading: str | None=..., content: str | None=..., kvps: dict | None=..., update_progress: ProgressUpdate | None=..., **kwargs)`
  - `stream(self, heading: str | None=..., content: str | None=..., **kwargs)`
  - `output(self)`
- `LogOutput` (no explicit base class)
- `Log` (no explicit base class)
  - `log(self, type: Type, heading: str | None=..., content: str | None=..., kvps: dict | None=..., update_progress: ProgressUpdate | None=..., id: Optional[str]=..., **kwargs) -> LogItem`
  - `set_progress(self, progress: str, no: int=..., active: bool=...)`
  - `set_initial_progress(self)`
  - `output(self, start=..., end=...)`
  - `reset(self)`
- Top-level functions:
- `_lazy_mark_dirty_all(reason: str | None=...) -> None`
- `_lazy_mark_dirty_for_context(context_id: str, reason: str | None=...) -> None`
- `_truncate_heading(text: str | None) -> str`
- `_truncate_progress(text: str | None) -> str`
- `_truncate_key(text: str) -> str`
- `_truncate_value(val: T) -> T`
- `_truncate_content(text: str | None, type: Type) -> str`
- Notable constants/configuration names: `_MARK_DIRTY_ALL`, `_MARK_DIRTY_FOR_CONTEXT`, `MASKING_FAILURE_REDACTION`, `T`, `HEADING_MAX_LEN`, `CONTENT_MAX_LEN`, `RESPONSE_CONTENT_MAX_LEN`, `KEY_MAX_LEN`, `VALUE_MAX_LEN`, `PROGRESS_MAX_LEN`.

## Runtime Contracts

- Helper modules own reusable framework APIs and must preserve public callers unless all callers, tests, and docs are updated together.
- Update this file whenever public functions, classes, persistence behavior, path/security assumptions, side effects, or cross-module contracts change.
- Secret masking is a confidentiality boundary: secret-manager acquisition or per-value masking failure must never return the original candidate string/object to log output, progress, state snapshots, or persistence.
- When the secret manager itself is unavailable, all string leaves in the candidate structure are replaced with the fixed `MASKING_FAILURE_REDACTION` sentinel because the runtime cannot prove any candidate string is safe.
- When only one `mask_values()` call fails, redact that leaf and continue masking sibling leaves so one failure does not expose the parent object or unnecessarily discard safe siblings.
- Masking-failure diagnostics may include only the exception type and a fixed message; never include the exception message or candidate value because either may contain secret material.
- Observed side-effect areas: filesystem writes, filesystem deletion, settings/state persistence, secret handling, scheduler state.
- Imported dependency areas include: `collections`, `copy`, `dataclasses`, `helpers.secrets`, `helpers.strings`, `json`, `logging`, `threading`, `time`, `typing`, `uuid`.

## Key Concepts

- Important called helpers/classes observed in the source: `TypeVar`, `dataclass`, `_MARK_DIRTY_ALL`, `_MARK_DIRTY_FOR_CONTEXT`, `truncate_text_by_ratio`, `cast`, `threading.RLock`, `self.set_initial_progress`, `self._update_item`, `self._notify_state_monitor`, `_lazy_mark_dirty_all`, `_lazy_mark_dirty_for_context`, `self._mask_recursive`, `self._mask_recursive_with_manager`, `self._redact_masking_failure`, `_truncate_progress`, `self.set_progress`, `LogOutput`, `_truncate_value`, `json.dumps`, `time.time`, `self.log._update_item`.
- Keep request/response, tool, or helper semantics documented here at the same time as source changes.

## Work Guidance

- Preserve public helper APIs used by core code and plugins unless every caller is updated.
- Keep path, auth, secret, persistence, network, and subprocess behavior explicit and bounded.
- Prefer adding cohesive helper functions here only when behavior is reused across modules.
- Never restore a fail-open `except Exception: return obj` path around secret masking.

## Verification

- Run `pytest tests/test_log_secret_masking.py` after changing masking behavior.
- Security regressions must cover secret-manager acquisition failure, per-string masking failure, nested dict/list containment, `LogItem.output()`, and progress state without requiring real secrets or network services.
- Run targeted tests for changed helper behavior; run security regressions for auth, filesystem, WebSocket, tunnel, upload, or secret-handling helpers.
- Related tests observed by source search:
  - `tests/test_browser_agent_regressions.py`
  - `tests/test_chat_compaction.py`
  - `tests/test_error_retry_plugin.py`
  - `tests/test_fasta2a_client.py`
  - `tests/test_file_tree_visualize.py`
  - `tests/test_history_compression_wait.py`
  - `tests/test_http_auth_csrf.py`
  - `tests/test_log_secret_masking.py`
  - `tests/test_mcp_handler_multimodal.py`

## Child DOX Index

No child DOX files.
