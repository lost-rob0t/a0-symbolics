# Prolog Context Compiler Plugin DOX

## Purpose

- Own the Prolog-RLM provider-context projection for Agent Zero.
- Keep symbolic selection, dependencies, budgeting, and fingerprints in Prolog.

## Ownership

- `helpers/catalog.py` adapts enabled Agent Zero tools, MCP declarations, skills, and DOX into bounded inert units.
- `helpers/working_context.py` and `helpers/projection.py` own host-side working-message and native-schema application.
- `helpers/transport.py` and `helpers/bridge.py` own bounded sidecar supervision and activation.
- `prolog/context_worker.pl` owns the closed JSON worker entry point.
- `extensions/` owns prompt interception, eager-catalog removal, final working-context compilation, and native-schema filtering.

## Local Contracts

- `_symbolics` owns whether this plugin is active; do not add a second runtime-mode authority here.
- When this plugin is active in RLM mode, the compiler path is enabled by default.
- Python gathers and applies projections; Prolog alone selects units and computes symbolic policy.
- Prompt visibility never grants tool authority, and native schemas may only be removed by a projection.
- Tools registered through `register_permanent_tools` remain provider-visible whenever they are enabled and allowed by Agent Zero.
- Catalog construction must load the paired Prolog-RLM core declaration explicitly; permanent visibility must not depend on plugin import order.
- Source-checkout mode and installed `library(adaptors/rlm_agent_zero_adapter)` mode are both supported.
- Crash, timeout, malformed JSON, missing fields, and oversized replies fail explicitly; none may become an empty successful projection.
- Persisted history stays separate from the bounded provider-visible working projection.

## Work Guidance

- Add inert metadata adapters rather than copying Prolog ranking or budget logic into Python.
- Keep full eager local, MCP, and skill catalogs hidden only while the compiler is active.
- Preserve the smallest stable always-visible core and measure prompt tokens after changes.

## Verification

- Run `pytest plugins/_prolog_context_compiler/tests` against the intended Prolog-RLM checkout.
- Run `tests/test_default_prompt_budget.py` and tool-policy tests.
- Verify native/RLM coordinator activation, sidecar restart, missing-tool retention, native-schema filtering, and long-context bounds.

## Child DOX Index

No child DOX files.
