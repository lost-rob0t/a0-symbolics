# Prolog-RLM Runtime

This bundled plugin is Agent Zero's typed bridge to the stable Prolog-RLM
runtime. Python owns JSON-lines transport, supervision, Agent Zero metadata
adaptation, bounded output, and tool/UI glue. Prolog-RLM owns symbolic context
selection, completion, recursive queries, supervised agents, plans,
capabilities, authority, durable effects, graphs, artifacts, Specs, MCP,
cancellation, tracing, usage, and structured outcomes.

The agent-facing `prolog_rlm` tool exposes only a fixed operation catalog. It
never accepts arbitrary Prolog, `call/1`, callable terms, credentials, shell
commands, or ambient filesystem authority. `direct` and `complete` compile the
live Agent Zero context through the Prolog context compiler first and use the
Prolog-RLM production OpenRouter provider; `direct` runs the bounded
provider-native direct agent loop with recursion enabled, and `complete` merges
the compiled projection with the caller's explicit context. Both inherit
credentials only from the host process environment. Results and errors never
include the API key.

`validate_tools` sends inert declarations for the tools Agent Zero has already
enabled. Prolog validates and groups them as external packs. Visibility,
registration, capabilities, authority, and effect admission remain separate;
pack validation grants nothing.

The bundled production pack adds three thin Agent Zero adapters and marks them
permanent through the context compiler's code-owned registration API:

- `exec(lang, source_code)` reuses the canonical terminal, Python, and Node.js
  execution implementation;
- `git` exposes bounded read-only status, branch, diff, show, log, and grep;
- `patch` reuses the canonical text-editor patch engine and its stale-read
  protections.

Together with the permanently retained `text_editor`, `code_execution_tool`,
and `prolog_rlm` tools, these cover the core execution, repository inspection,
diff/patch, editing, and symbolic-runtime surface. Tool calls still pass through
the ordinary Agent Zero lifecycle and scoped policy gate. The external Prolog
pack validates declarations and capability shape; it does not create ambient
shell or filesystem authority.

The runtime and context plugins share one supervised transport implementation,
but use distinct persistent workers because a completion may legitimately take
longer than a context compile. A crash, malformed reply, oversized reply, or
timeout is an explicit failure; transport faults trigger one clean worker
restart and never become an empty-success projection.

Set `PROLOG_RLM_ROOT` for a source checkout, or leave it unset when
`library(rlm)` is installed by the Nix package. Optional `OPENROUTER_MODEL`
selects the model; `OPENROUTER_API_KEY` remains in `.env` and is never committed.
