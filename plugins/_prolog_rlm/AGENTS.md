# Prolog-RLM Plugin DOX

## Purpose

- Own the single Agent Zero model-turn bridge to Prolog-RLM.
- Keep context selection and model invocation in Prolog while Agent Zero remains the tool execution-policy authority.

## Ownership

- `helpers/bridge.py` owns the persistent typed runtime bridge.
- `helpers/model_turn.py` owns Agent Zero message/tool adaptation and native result reconstruction.
- `prolog/runtime_worker.pl` owns the closed context-compile, provider-turn, and runtime-action protocol.
- `tools/prolog_rlm.py` owns the optional agent-facing runtime introspection tool.
- `tests/` owns routing, bridge, schema, and fail-closed verification.

## Local Contracts

- Never accept arbitrary Prolog goals or callable terms from model data.
- Every main chat-model turn must fail closed through Prolog-RLM while this plugin is enabled; do not fall back to Agent Zero's direct model transport.
- Prolog-RLM returns native tool calls, but execution remains subject to Agent Zero's normal lifecycle, scoped tool policy, intervention handling, and plugin hooks.
- Context compilation is part of the same Prolog worker turn; do not reintroduce a separate context-compiler plugin.
- The worker's `agent` action runs Prolog-RLM's bounded provider-native direct loop (`rlm_direct/4`) with no registry and no extra authority; it is observation and bounded compute, not an execution path.
- The worker file loads into the Prolog `user` module; never define worker helpers whose names collide with predicates exported by Prolog-RLM modules (a same-named `user` helper changes module import resolution and silently drops runtime validation clauses).
- Credentials stay in the inherited process environment and must never appear in requests, results, logs, or repository files.

## Work Guidance

- Extend the closed action catalog instead of adding an arbitrary-call escape hatch.
- Keep native tool schemas strict and bounded; visibility never grants execution authority.
- Update this file, the README, prompt, and tests when the turn contract changes.

## Verification

- Run `pytest plugins/_prolog_rlm/tests` with `PROLOG_RLM_TEST_ROOT` pointing at the intended Prolog-RLM checkout.
- Run the repository Responses, prompt-budget, and tool-policy tests after changing visibility or schemas.
- Verify a live container turn calls an existing Agent Zero tool and completes through `response`.

## Child DOX Index

No child DOX files.
