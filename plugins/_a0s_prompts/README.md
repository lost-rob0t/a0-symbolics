# Symbolics Prompt Overlay

This bundled plugin carries the a0-symbolics prompt deltas as plugin-owned
files instead of modifications to upstream-owned prompt sources. Agent Zero
resolves prompt files through `helpers.subagents.get_paths`, where enabled
plugin directories are searched before the framework `prompts/` and
`agents/<profile>/prompts/` roots, so these files override their upstream
counterparts while upstream files stay clean for upstream replays.

## Contents

- `prompts/agent.system.main.solving.md` — condensed, action-first
  problem-solving workflow (context debloat).
- `prompts/agent.system.tool.code_exe.md` — trimmed code-execution tool
  catalog entry (drops redundant JSON examples).
- `agents/agent0/prompts/agent.system.main.role.md` and
  `agents/{developer,hacker,researcher}/prompts/agent.system.main.specifics.md`
  — persona positioning that frames security work as professional engagement
  behavior instead of refusal-driven phrasing.

## Maintenance rules

- Upstream prompt changes do not silently apply while these overrides exist;
  `scripts/upstream-sync` replays and the fork-surface report keep the delta
  visible. Review upstream prompt rewrites after each upstream sync and fold
  wanted changes into these files deliberately.
- Do not add extensions or hooks here; this plugin is prompt-file ownership
  only. Behavior belongs in the plugins that implement it.

## Verification

- `pytest tests/test_default_prompt_budget.py` locks the rendered budget and
  guardrails that motivated these overrides.
- The prompt-override precedence is covered by
  `tests/test_a0s_prompt_overlay.py`.