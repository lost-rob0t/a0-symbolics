# Prolog-RLM Plugin DOX

## Purpose

- Own the Agent Zero bridge to Prolog-RLM and its production coding-tool pack.
- Keep symbolic selection and validation in Prolog while Agent Zero remains the execution-policy authority.

## Ownership

- `helpers/bridge.py` owns the persistent typed runtime bridge.
- `prolog/` owns the closed worker protocol and external Agent Zero pack loader.
- `tools/` owns the agent-facing RLM, execution, Git, and patch adapters.
- `hooks.py` owns the single permanent-tool declaration consumed lazily by the context compiler.
- `prompts/` owns their provider-visible schemas and operating contracts.
- `tests/` owns bridge, adapter, and pack boundary verification.

## Local Contracts

- `_symbolics` owns whether this plugin and the paired context compiler are active; do not create an independent runtime-mode switch here.
- Never accept arbitrary Prolog goals or callable terms from model data.
- Production coding adapters must reuse Agent Zero's existing execution and editor implementations; do not create a second shell or patch engine.
- Tool execution remains subject to the normal Agent Zero tool lifecycle, scoped tool policy, intervention handling, and plugin hooks.
- `git` is a closed read-only inspection adapter. Mutating Git operations remain explicit terminal work through an authorized execution tool.
- `patch` retains the text editor's stale-read and structured-patch protections.
- Credentials stay in the inherited process environment and must never appear in requests, results, logs, or repository files.

## Work Guidance

- Extend the closed action catalog instead of adding an arbitrary-call escape hatch.
- Keep tool schemas strict and bounded, and keep permanent-tool registration code-owned.
- Update this file, the README, prompts, and tests when a tool contract changes.

## Verification

- Run `pytest plugins/_prolog_rlm/tests` with `PROLOG_RLM_TEST_ROOT` pointing at the intended Prolog-RLM checkout.
- Run the plugin Prolog test and the context-compiler integration tests.
- Run the repository prompt-budget and tool-policy tests after changing visibility or schemas.
- Verify `_symbolics` native mode excludes this plugin and RLM mode activates it together with the compiler.

## Child DOX Index

No child DOX files.
