### prolog_rlm
Prolog-RLM runtime status, completion, and demos
args: `action`; action-specific `name`, `prompt`, `query`, `context`, `budget`
actions:
- `status`, `catalog`: inspect the stable runtime and bridge
- `demo`: deterministic `context`, `tool`, `recursion`, `agent`, `graph`, or `mcp`
- `direct`: one bounded OpenRouter-backed model call
- `complete`: bounded recursive completion over query and context
never send Prolog code callable terms credentials shell commands or filesystem paths
