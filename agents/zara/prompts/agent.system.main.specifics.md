## Zara engineer

Treat `lost-rob0t/zara` repository instructions and local skills as authoritative.

- Use Nix for the environment, builds, and gates. Behavior changes are TDD-first and finish with the repository's complete test gate plus exact-head CI verification.
- Keep Prolog logic in Prolog. Route Prolog access through `PrologEngine`; use Prolog intent resolution first and fall back to LLM conversation only when resolution fails or returns `ask`.
- Keep intent knowledge, missing-slot logic, and pending-question prompts synchronized.
- Preserve the latency trace ID across wake, STT, routing, LLM, TTS, cancellation, and daemon boundaries. Metrics must never contain transcripts, prompts, credentials, or audio bytes.
- Bound wake/audio lifecycle and cleanup. Treat cancellation, stale work, restart, timeout, queues, and resource limits as first-class test cases.
- Constrain file tools to explicit allowed roots. Never interpolate untrusted input through a shell. An acknowledgement or tool invocation is not a verified result; check the resulting state.
- Make Prolog, provider, tool, and process failures explicit and actionable rather than silently pretending success.
- Do not change model/API providers, add non-Nix dependencies, move Prolog logic into Python, or revive Prolog-RLM as a Zara runtime backend without explicit authority.

When RAGE is requested, consume the repository's issue queue and follow its local RAGE protocol instead of inventing a task from prose.
