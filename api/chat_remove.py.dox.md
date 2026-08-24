# chat_remove.py DOX

## Purpose

- Own the chat-removal API endpoint.
- Keep destructive context and filesystem removal behind validated context identity.

## Ownership

- `RemoveChat.process(...)` coordinates scheduler cancellation, live-context reset/removal, persisted-chat deletion, scheduler reload, and global state invalidation.

## Runtime Contracts

- HTTP handler derives from `helpers.api.ApiHandler` and preserves the existing authenticated/CSRF route policy supplied by the framework.
- `input["context"]` is caller-controlled and must pass `helpers.context_utils.validate_context_id` before scheduler, registry, or filesystem side effects.
- Invalid context IDs fail before `persist_chat.remove_chat()` or any destructive action.
- Persistence remains responsible for its own independent chat-root containment checks; endpoint validation is defense in depth.
- Successful removal preserves the existing response shape: `{ "message": "Context removed." }`.

## Side Effects

- Cancels scheduler work for the context.
- Resets/removes a live `AgentContext` when present.
- Deletes persisted chat state through `persist_chat.remove_chat`.
- Reloads/removes scheduler tasks and marks global state dirty.

## Work Guidance

- Validate destructive identifiers before the first mutation.
- Keep persistence/filesystem policy in shared helpers rather than duplicating path construction here.
- Preserve authentication, CSRF, and scheduler semantics when changing removal behavior.

## Verification

- Run `pytest tests/test_context_id_security.py`.
- Verify traversal/absolute/control-character IDs cannot reach persistence deletion and valid generated IDs retain normal removal behavior.

## Child DOX Index

No child DOX files.
