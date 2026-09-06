# Tool Execute After Extensions DOX

## Purpose

- Own backend processing immediately after tool execution.

## Ownership

- Ordered Python files own post-tool secret masking and terminal scheduler-result attestation.

## Local Contracts

- Mask secrets before tool results reach history, UI, or model-visible context.
- Do not alter tool `break_loop` or response semantics unless the hook contract owns that behavior.
- After masking and integration-specific response hooks run, attest non-empty scheduler `response` tool completions so only terminal output can be promoted between occurrences.

## Work Guidance

- Coordinate with tool implementations and history hooks when changing tool result data.

## Verification

- Smoke-test tool execution with sensitive output after changes.

## Child DOX Index

No child DOX files.
