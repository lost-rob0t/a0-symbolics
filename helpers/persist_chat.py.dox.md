# persist_chat.py DOX

## Purpose

- Own persisted chat/context serialization, loading, and destructive chat/message-file cleanup.
- Keep every context-derived filesystem path confined to the canonical chat store.

## Ownership

- `CHATS_FOLDER` is the canonical persisted-chat root.
- `_chat_path(ctxid, *parts)` owns defensive path construction and resolved containment.
- `helpers.context_utils.validate_context_id` owns canonical opaque context-ID syntax.
- `get_chat_folder_path`, `get_chat_msg_files_folder`, and `_get_chat_file_path` must route through `_chat_path`.
- `save_tmp_chat`, `load_tmp_chats`, `remove_chat`, and `remove_msg_files` own persistence lifecycle operations.

## Runtime Contracts

- Context IDs are identifiers, never path components supplied without validation.
- Every persistence path validates the context ID and independently proves `Path.resolve()` remains beneath the resolved `usr/chats` root.
- Invalid IDs fail before read/write/delete provider or filesystem side effects.
- Message-file paths inherit the same containment contract as chat JSON paths.
- Unsafe legacy chat folder/file names are reported and skipped; they are never resolved or deleted as filesystem paths.
- Persisted `chat.json` IDs are validated before constructing `AgentContext` objects. Unsafe legacy records fail that individual load without preventing other valid chats from loading.
- When present, a persisted `chat.json` ID must match its containing chat folder so loading cannot detach context identity from its storage path.
- `saved_chat_ids()` excludes/report unsafe legacy directory names instead of publishing them as live context identity.
- Serialized chats store `agent_profile` both at context level and per serialized agent so subordinate profiles survive restart.
- Chat saves write/fsync a same-directory temporary file, atomically replace `chat.json`, and fsync the directory.
- Contexts are marked with `SAVED_CHAT_CONTEXT_DATA_KEY` only after successful save/load.

## Work Guidance

- Do not weaken `_chat_path` containment because upstream/API boundaries also validate IDs; persistence must remain independently safe.
- New chat-owned files/directories must use `_chat_path` rather than string joining context IDs into paths.
- Keep unsafe-legacy handling non-destructive. Migration/renaming policy may evolve separately, but unsafe names must never be acted on as paths.
- Preserve provider-response cleanup semantics unless changing the separate provider-cleanup lifecycle.

## Verification

- Run `pytest tests/test_context_id_security.py` for traversal, absolute path, separator, control-character, Unicode, length, and sentinel-deletion coverage.
- Run nearby persistence regressions including `tests/test_api_chat_lifetime.py`, `tests/test_persist_chat_log_ids.py`, and `tests/test_subagent_profiles.py` after persistence changes.
- Security coverage must prove direct internal calls to chat/message removal cannot escape the chat root even if an API boundary is bypassed.

## Child DOX Index

No child DOX files.
