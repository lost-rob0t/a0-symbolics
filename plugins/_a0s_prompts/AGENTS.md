# Symbolics Prompt Overlay DOX

## Purpose

- Own the bundled Symbolics prompt overrides that would otherwise modify
  upstream-owned prompt files.

## Ownership

- `prompts/` and `agents/<profile>/prompts/` in this plugin override the
  framework prompt sources through the standard plugin path precedence.
- `README.md` documents the contents and maintenance rules.

## Local Contracts

- `always_enabled` stays true; disabling this plugin silently reverts to
  upstream prompt text and is a distribution-level decision.
- Files must keep the same relative paths and basenames as the upstream
  prompt files they replace.
- No extensions, hooks, tools, or API handlers belong in this plugin.

## Work Guidance

- After every upstream sync, review the upstream versions of overridden
  prompts and fold wanted changes into these files deliberately.

## Verification

- Run `pytest tests/test_a0s_prompt_overlay.py` and
  `pytest tests/test_default_prompt_budget.py`.

## Child DOX Index

No child DOX files.