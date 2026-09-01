# Zara Bridge Plugin DOX

## Purpose

- Own the optional Agent Zero-to-Zara delegation boundary.
- Reuse Zara's existing daemon client instead of duplicating its transport protocol.

## Ownership

- `plugin.yaml` owns plugin metadata.
- `.toggle-0` owns the bundled disabled-by-default state.
- `default_config.yaml` owns endpoint, binary, timeout, and size defaults.
- `helpers/client.py` owns bounded Zara CLI invocation.
- `tools/zara_bridge.py` owns the agent-facing one-turn delegation tool.
- `prompts/` owns agent guidance for the tool.

## Local Contracts

- The plugin must remain disabled by default in the bundled tree.
- User-level activation may override the bundled `.toggle-0` through the normal plugin toggle system.
- Invoke Zara only as an argv subprocess using `zara --connect ENDPOINT MESSAGE`; never use a shell command string.
- Do not implement or vendor a second ZARA/1 or ZeroMQ client here.
- Require an explicit daemon endpoint from plugin config or `A0_ZARA_ENDPOINT`.
- Keep subprocess time, input size, and returned output bounded.
- Do not log or persist messages, daemon credentials, transport keys, or private Zara responses from this plugin.
- Do not modify Agent Zero core runtime files to support this bridge.

## Work Guidance

- Keep the bridge narrow: one Agent Zero tool maps to one Zara text turn.
- Add new Zara capabilities at the Zara client boundary first, then consume them here rather than bypassing that boundary.
- Avoid reciprocal auto-routing loops between Zara and Agent Zero.

## Verification

- Run `pytest plugins/_zara_bridge/tests` after bridge changes.
- Verify the bundled `.toggle-0` exists and `always_enabled` remains false.
- Use a fake Zara executable for deterministic subprocess tests; tests must not require a live daemon.

## Child DOX Index

No child DOX files.
