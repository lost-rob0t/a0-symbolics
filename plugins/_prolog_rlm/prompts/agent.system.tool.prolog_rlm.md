### prolog_rlm
Prolog-RLM context, completion, demos, and external-pack validation
args: `action`; action-specific `name`, `prompt`, `query`, `context`, `budget`
actions:
- `status`, `catalog`: inspect the stable runtime and bridge
- `demo`: deterministic `context`, `tool`, `recursion`, `agent`, `graph`, or `mcp`
- `validate_tools`: validate enabled Agent Zero/MCP declarations without granting authority
- `direct`: one bounded OpenRouter-backed model call
- `complete`: bounded recursive completion over query and context
never send Prolog code callable terms credentials shell commands or filesystem paths
