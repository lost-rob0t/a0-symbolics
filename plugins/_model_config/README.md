# Model Configuration

Manage the reusable model presets used for Agent Zero's main, utility, and embedding models.

## Model Presets

- `Default` is always present, appears first, and cannot be renamed or deleted.
- Every runtime configuration resolves from a preset. There is no separate durable model configuration layer.
- Preset definitions are global and live in `usr/plugins/_model_config/presets.yaml`. Plugin defaults in `mode_presets_fallback.yaml` are used only when a saved collection cannot be initialized.
- Non-default presets may omit advanced fields or model slots; omitted values resolve from `Default`, while provider-specific `kwargs` are replaced or cleared instead of leaking between providers.
- API keys remain in the approved environment/settings flow and are never written into preset YAML.

## OpenRouter Prompt Caching

Agent Zero treats OpenRouter prompt caching as a provider/model capability instead of adding Anthropic-style `cache_control` markers to every OpenRouter request.

- OpenAI, xAI/Grok, Moonshot, DeepSeek, Z.AI, and Gemini 2.5+ use their documented provider-side automatic/implicit prompt caches. Agent Zero does not inject `cache_control` blocks for these families, so tool turns can remain on the Responses transport where supported.
- Anthropic defaults to explicit per-block `cache_control` markers. OpenRouter documents those breakpoints as portable across Anthropic-compatible endpoints including Bedrock and Vertex. A caller may instead set top-level `cache_control` in model kwargs (for example `{"type":"ephemeral","ttl":"1h"}`); that opts into OpenRouter's automatic Anthropic cache mode, which currently routes only to Anthropic direct.
- Alibaba/Qwen explicit cache markers are used only for the exact OpenRouter-documented models: `qwen/qwen3-max`, `qwen/qwen-plus`, `qwen/qwen3.6-plus`, `qwen/qwen3-coder-plus`, and `qwen/qwen3-coder-flash`. Unsupported snapshots such as `qwen/qwen3.5-plus-02-15` and `qwen/qwen3.5-flash-02-23` are deliberately left unmarked.
- Unknown OpenRouter model families are passive: Agent Zero does not invent cache markers. Any provider-side implicit caching can still work normally.
- Every OpenRouter call inside an Agent Zero context gets a stable `session_id` unless the preset/caller already supplied one. OpenRouter uses it for sticky provider routing so multi-turn agents return to the endpoint holding the warm prompt cache.
- OpenAI routes also get a stable `prompt_cache_key` derived from reusable prompt/tool material. User-supplied `prompt_cache_key`, `prompt_cache_options`, and legacy `prompt_cache_retention` values are preserved. OpenRouter-specific cache/routing parameters are carried through LiteLLM's `extra_body` compatibility path.
- OpenRouter response caching (`X-OpenRouter-Cache`) is a separate whole-response replay feature and is **not** enabled automatically. It may be useful for deterministic tests/retries but should not silently replay normal agent/tool turns.

Current provider behavior is based on OpenRouter's Prompt Caching documentation. When OpenRouter changes a model family's caching contract, update `helpers/transport_compat.py` and its policy-matrix regressions together.

## Scoped Selection

Global, project, project/profile, and agent-profile scopes store only a preset name in their standard plugin `config.json`:

```json
{"model_preset": "Balance"}
```

For example, a project selection is stored at:

```text
/a0/usr/projects/<project>/.a0proj/plugins/_model_config/config.json
```

The normal plugin resolution order selects the most specific available reference. A missing or deleted reference safely resolves to `Default`. Chats may store an explicit preset reference in `chat_model_override`; clearing it returns the chat to its scoped selection.

## User Interfaces

- Agent Settings shows the global selection, its three resolved models, and actions for preset editing, API keys, and per-project/agent settings.
- The full plugin settings modal uses the generic scope selector and stores only the chosen preset at that scope.
- The closed chat switcher shows the effective preset plus the main model's short name; its menu supports a chat-only selection or returning to the scoped preset.
- The adjacent profile switcher shows the active agent's effective title and avatar and links to Create, Edit, and Manage agents.
- The preset editor exposes the shared API key for each selected provider and saves key changes separately from secret-free preset definitions.
- Project Settings selects from the same global preset definitions.

## Initial Presets And Migration

The startup migration converts the prior global full model configuration into `Default`, preserves existing global presets, promotes distinct scoped full configurations and legacy project presets into uniquely named global presets, and rewrites scoped config files to selection-only JSON. Original files receive a `.pre-unified-presets.bak` backup before replacement; the migration is idempotent.

At every startup, legacy migration runs first. If `usr/plugins/_model_config/presets.yaml` then exists, initialization returns immediately without network access. Otherwise the plugin makes one bounded request for [`agent0ai/a0-presets/model_presets.yaml`](https://github.com/agent0ai/a0-presets/blob/main/model_presets.yaml), validates the whole collection, removes secret fields, and saves it locally. A download, parse, or validation failure processes and saves plugin-local `mode_presets_fallback.yaml` through the same validation path, so initialization remains usable offline.

## Key Files

- `helpers/model_config.py` owns preset validation, resolution, compatibility config shapes, and runtime model construction.
- `helpers/transport_compat.py` owns reasoning-effort compatibility plus the OpenRouter prompt-cache/sticky-routing policy.
- `api/model_presets.py` owns global preset editing, scoped selection, and reference repair after rename/delete/reset.
- `extensions/python/startup_migration/_10_migrate_model_config.py` owns legacy conversion.
- `extensions/python/startup_migration/_20_bootstrap_model_presets.py` owns missing-collection initialization and plugin-local fallback.
- `extensions/python/startup_migration/_90_transport_compat.py` installs transport compatibility once per process.
- `webui/preset-overview.html` is the shared Settings/plugin-settings summary widget.
- `webui/main.html` is the preset editor.

## Plugin Metadata

- Name: `_model_config`
- Settings section: `agent`
- Per-project config: `true`
- Per-agent config: `true`
- Always enabled: `true`
