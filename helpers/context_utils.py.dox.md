# context_utils.py DOX

## Purpose

- Own shared context lookup/creation helpers and the canonical context-ID trust boundary.
- Keep API and WebSocket context selection from treating caller-controlled identifiers as paths.

## Ownership

- `validate_context_id(ctxid)` owns the canonical opaque identifier syntax.
- `use_context(lock, ctxid, create_if_not_exists=...)` owns synchronized lookup/creation and validates every non-empty supplied ID before lookup or creation.

## Runtime Contracts

- Context IDs are opaque identifiers, never filesystem paths.
- Accepted supplied IDs are 1-128 ASCII letters, digits, `_`, or `-`; generated Agent Zero IDs remain compatible.
- Reject separators, traversal components, absolute/URL-like strings, whitespace/control characters, Unicode, and overlong values before context lookup/creation.
- Empty `ctxid` remains the explicit `use_context` sentinel for selecting the first context or creating a generated default context; it is not a valid persistent context identifier.
- Newly constructed contexts reconcile their active profile against Global availability before returning.
- Existing context lookups return the stored context unchanged; explicit profile and project transitions own any repair.

## Work Guidance

- Reuse `validate_context_id` at external context boundaries instead of inventing endpoint-specific validators.
- Persistence code must still enforce its own resolved-path containment; boundary validation is defense in depth, not a substitute for filesystem ownership checks.
- Preserve public helper APIs used by core code and plugins unless every caller is updated.

## Verification

- Run `pytest tests/test_context_id_security.py` after context-ID changes.
- Run `tests/test_projects.py` for context creation/profile reconciliation behavior.
- Security regressions must prove invalid IDs cannot create/select filesystem-addressable contexts.

## Child DOX Index

No child DOX files.
