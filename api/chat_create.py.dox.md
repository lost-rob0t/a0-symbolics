# chat_create.py DOX

## Purpose

- Own the chat-creation API endpoint.
- Keep caller-supplied current/new context identifiers behind the canonical context-ID boundary before context lookup or creation.

## Ownership

- `CreateChat.process(...)` validates identity, creates/selects the new context, inherits allowed project/model state, reconciles the active profile, and marks global state dirty.

## Runtime Contracts

- HTTP handler derives from `helpers.api.ApiHandler` and preserves the framework authentication/CSRF policy.
- A supplied non-empty `current_context` must pass `helpers.context_utils.validate_context_id` before lookup.
- A supplied `new_context` must pass the same validator; omission generates the normal Agent Zero ID and validates it as an invariant check.
- An explicitly empty/unsafe `new_context` is invalid and returns HTTP 400 before `AgentContext.get`, `self.use_context`, project inheritance, or other mutation.
- A newly created chat reconciles its profile after project inheritance so it never keeps a profile unavailable in the inherited scope.
- This endpoint does not own collision/reuse semantics for otherwise valid IDs; those remain a separate chat-lifecycle contract.
- Successful response shape remains `{ "ok": true, "ctxid": ..., "message": "Context created." }`.

## Side Effects

- May create/select an AgentContext.
- May inherit project metadata and an allowed model override.
- Reconciles profile/project state and marks global chat state dirty.

## Work Guidance

- Validate caller-controlled IDs before the first context lookup/mutation.
- Reuse the shared validator; do not create endpoint-specific path sanitizers.
- Preserve authentication, CSRF, inheritance, and model-override semantics.

## Verification

- Run `pytest tests/test_context_id_security.py`.
- Verify malformed `new_context` values return 400 without reaching context creation.
- Run nearby chat lifecycle/browser regressions when changing valid chat creation behavior.

## Child DOX Index

No child DOX files.
