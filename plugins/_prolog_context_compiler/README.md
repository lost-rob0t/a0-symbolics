# Prolog Context Compiler

This plugin replaces Agent Zero's eager provider-visible local-tool, MCP-tool,
and skill catalogs with a per-turn projection compiled by Prolog-RLM. Runtime
tool registration and `_tool_access` authorization are unchanged: compiler
visibility can only remove schemas from a provider call and cannot grant tool
execution.

`helpers.catalog.register_permanent_tools(...)` is the code-owned adapter API
for essential tools. Permanent declarations are sent as inert metadata; the
public `adaptors/rlm_agent_zero_adapter` module in Prolog-RLM owns their explicit
selection and packing semantics. The default permanent set keeps final
response, editing, code execution, delegation, input, wait, skill loading, and
the full RLM facade visible whenever those tools are actually registered and
authorized.

The paired Prolog-RLM runtime plugin registers `exec`, `git`, `patch`, and
`prolog_rlm` from its single code-owned declaration when the compiler builds a
catalog. This lazy registration does not depend on plugin import order, so the
production editing core cannot disappear merely because the runtime hook has
not otherwise been imported yet. External tool packs use the same registration
API for any additional tools that must remain visible.

The bridge supervises one persistent SWI-Prolog worker. Requests and replies are
bounded line-delimited JSON. A timeout, crash, mismatched reply, malformed JSON,
or empty projection fails the provider call explicitly; there is no silent
empty-selection fallback. A stateless request is retried once after transport
failure with the same request ID, so a restarted worker produces the same
fingerprint and does not duplicate durable symbolic state.

Set `PROLOG_RLM_ROOT` or `prolog_rlm_root` while developing against a checkout.
Packaged environments should set `enabled: true` or `PROLOG_RLM_ENABLED=1` and
expose the installed Prolog-RLM pack through `SWIPL_PACK_PATH` instead.

The implicit `Agent.prepare_prompt` end hook also adapts current project/DOX
instructions and older message history into bounded inert units. Prolog selects
the older working set; Python retains a configurable recent-message window,
replaces unbounded prior history with the rendered symbolic projection, and
enforces a hard final input-token limit including the native tool schemas that
the provider actually receives. Persisted chat history remains unchanged.
