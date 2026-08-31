# Prolog-RLM Runtime

This bundled plugin is Agent Zero's single typed model-turn bridge to the stable
Prolog-RLM runtime. Python adapts Agent Zero messages and native tool schemas,
supervises the JSON-lines worker, and reconstructs Agent Zero's native turn
result. Prolog-RLM compiles the provider-visible context and performs the model
request. There is no separate context-compiler plugin and no direct-model
fallback while this plugin is enabled.

The agent-facing `prolog_rlm` tool exposes only a fixed operation catalog. It
never accepts arbitrary Prolog, `call/1`, callable terms, credentials, shell
commands, or ambient filesystem authority. `direct` uses the runtime's one-call
`llm_query` contract, `agent` runs the bounded provider-native direct agent
loop (`rlm_direct/4`) with runtime context operations and registered tools, and
`complete` uses bounded recursive completion. All of them use the Prolog-RLM
production OpenRouter provider and inherit credentials only from the host
process environment. Results and errors never include the API key.

Each main turn sends inert declarations for the tools Agent Zero has already
enabled. Prolog-RLM selects the relevant context and tool schemas, calls the
configured OpenRouter model through its normalized provider API, and returns
native function calls. Agent Zero then executes those calls through its normal
tool lifecycle and scoped policy gate. Visibility, capability, and execution
authority remain separate.

The integration uses Agent Zero's existing tools directly, including
`code_execution_tool` and `text_editor`; it does not maintain duplicate exec,
Git, or patch adapters. A crash, malformed reply, oversized reply, timeout, or
unsupported non-OpenRouter chat preset is an explicit failure and never falls
back to a direct model call.

Set `PROLOG_RLM_ROOT` for a source checkout, or leave it unset when
`library(rlm)` is installed by the Nix package. The active Agent Zero OpenRouter
preset selects the model unless `openrouter_model` explicitly overrides it.
`OPENROUTER_API_KEY` remains in the process environment and is never committed.
