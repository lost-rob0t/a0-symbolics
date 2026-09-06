### prolog_rlm
Prolog-RLM context, completion, demos, and external-pack validation
args: `action`; action-specific `name`, `prompt`, `query`, `context`, `budget`
actions:
- `status`, `catalog`: inspect the stable runtime and bridge
- `demo`: deterministic `context`, `tool`, `recursion`, `agent`, `graph`, or `mcp`
- `validate_tools`: validate enabled Agent Zero/MCP declarations without granting authority
- `direct`: bounded OpenRouter-backed direct agent session over the compiled Agent Zero context, recursion enabled
- `complete`: bounded recursive completion over the compiled context plus explicit context
never send Prolog code callable terms credentials shell commands or filesystem paths
