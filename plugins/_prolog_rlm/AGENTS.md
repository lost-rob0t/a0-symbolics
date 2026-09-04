# Prolog-RLM Plugin DOX

## Purpose

- Own the Agent Zero bridge to Prolog-RLM and its production coding-tool pack.
- Keep symbolic selection and validation in Prolog while Agent Zero remains the execution-policy authority.

## Ownership

- `helpers/harness/` owns the typed host seam: `Transport`/`Envelope` over the runtime worker and the `PrologRLM` client (`RunResult`, typed errors, shared-instance caching).
- `helpers/loop.py` owns the core-loop model proxy (`PrologRLMModel`) that routes main-loop chat turns through the runtime per the reasoning-mode policy.
- `helpers/bridge.py` owns the persistent typed runtime bridge (compatibility shim for the harness and smoke tooling).
- `extensions/python/chat_model_call_before/` owns the core-loop model swap (`RouteReasoningMode`).
- `api/runtime_policy.py` owns the chat-UI policy endpoint (mode + context budget read/write).
- `webui/` owns the plugin settings form and the page-head policy control store.
- `prolog/` owns the closed worker protocol and external Agent Zero pack loader.
- `tools/` owns the agent-facing RLM, execution, Git, and patch adapters.
- `hooks.py` owns the single permanent-tool declaration consumed lazily by the context compiler.
- `prompts/` owns their provider-visible schemas and operating contracts.
- `tests/` owns harness, bridge, loop-policy, adapter, and pack boundary verification.

## Local Contracts

- Never accept arbitrary Prolog goals or callable terms from model data.
- Core-loop enforcement: when `core_loop_enabled`, every main-loop chat turn routes through `PrologRLMModel`; `direct` delegates to the inner A0 model (streaming preserved), `symbolic`/`symbolic-recursive`/`auto` turn through the runtime, which owns mode selection, recursion depth, and context ceilings. Runtime failures raise; they must never silently downgrade to native calls.
- Textless turns route validly: a turn with an empty user message derives its query from the newest message text (earlier messages stay context) so the runtime's non-empty-query contract holds; only a turn with no queryable text anywhere falls through to the inner model exactly like direct mode (a degenerate turn, not a runtime-failure downgrade).
- Worker request rejections report `runtime_request_error: <reason>` with the original term in `detail`; the bridge carries that detail on `PrologRuntimeBridgeError`. SWI's `Unknown message: ...` rendering must never reach host callers.
- `context_budget_percent` (default 30) resolves against the inner model's `ctx_length` each turn; the runtime enforces the ceiling via `context_options(max_bytes)`, not Python.
- Production coding adapters must reuse Agent Zero's existing execution and editor implementations; do not create a second shell or patch engine.
- `git` is a closed read-only inspection adapter. Mutating Git operations remain explicit terminal work through an authorized execution tool.
- `patch` retains the text editor's stale-read and structured-patch protections.
- Tool execution remains subject to the normal Agent Zero tool lifecycle, scoped tool policy, intervention handling, and plugin hooks.
- Credentials stay in the inherited process environment and must never appear in requests, results, logs, or repository files.

## Work Guidance

- Extend the closed action catalog instead of adding an arbitrary-call escape hatch.
- Keep tool schemas strict and bounded, and keep permanent-tool registration code-owned.
- Update this file, the README, prompts, and tests when a tool contract changes.

## Verification

- Run `pytest plugins/_prolog_rlm/tests` with `PROLOG_RLM_TEST_ROOT` pointing at the intended Prolog-RLM checkout.
- Run the plugin Prolog test and the context-compiler integration tests.
- Run the repository prompt-budget and tool-policy tests after changing visibility or schemas.

## Child DOX Index

No child DOX files.
