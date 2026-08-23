# OpenRouter prompt-cache policy

`transport_compat.py` is the compatibility boundary for OpenRouter prompt caching used by Agent Zero model presets.

## Contract

- Never treat `openrouter` itself as a single cache dialect.
- Automatic/implicit cache families receive no synthetic `cache_control` blocks.
- Anthropic defaults to explicit block breakpoints because those remain portable across Anthropic-compatible provider endpoints. A caller-provided top-level `cache_control` is preserved as an explicit opt-in to OpenRouter's direct-Anthropic automatic cache mode.
- Alibaba/Qwen block caching is enabled only for exact model slugs documented by OpenRouter. Unsupported snapshots and unknown families remain passive.
- DeepSeek uses the documented automatic cache path even when a specific provider also advertises an explicit caching mode.
- Every OpenRouter request should carry a stable Agent Zero context `session_id` unless the caller supplied one. This is provider-routing affinity, not a response cache key.
- OpenAI `prompt_cache_key` is derived from stable prompt/tool material, not the per-chat session id, unless the caller overrides it. User-provided prompt-cache options/retention are preserved.
- OpenRouter's whole-response cache (`X-OpenRouter-Cache`) is separate from provider prompt caching and must never be enabled implicitly here.
- All OpenRouter-only compatibility fields that may be stripped by the pinned LiteLLM path are forwarded through `extra_body`.

## Regression matrix

Tests must cover automatic OpenAI/Z.AI/DeepSeek/Gemini routes, Anthropic block and top-level modes, supported and unsupported Qwen slugs, passive unknown models, sticky `session_id`, manual overrides, OpenAI cache-affinity parameters, response-cache non-enablement, and every supported reasoning-effort value.
