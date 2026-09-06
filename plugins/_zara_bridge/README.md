# Zara Bridge

`_zara_bridge` lets Agent Zero delegate one text turn to an already-running Zara daemon.

The plugin is **disabled by default**. Its bundled `.toggle-0` keeps it out of the enabled plugin/tool set until the user explicitly enables it. A user-level `.toggle-1`, including one created by the Plugins UI, overrides the bundled default normally.

## Transport

The bridge does not implement Zara's ZeroMQ protocol itself. It executes the existing Zara client boundary with an argv-only subprocess:

```sh
zara --connect <endpoint> '<message>'
```

That path uses Zara's `ZmqZaraClient`, `SubmitTurn`, and normal daemon authentication/transport policy.

## Tool

When enabled, the plugin contributes `zara_bridge`:

- argument: `message`
- sends exactly one text turn
- returns Zara's user-facing response
- does not expose shell execution or raw Zara protocol operations

## Configuration

Bundled defaults:

```yaml
zara_binary: zara
endpoint: ""
timeout_seconds: 35
max_message_chars: 20000
max_output_chars: 50000
```

The endpoint is intentionally empty. Set it to the actual daemon endpoint rather than assuming a machine-specific runtime path.

Runtime environment overrides are also supported:

```sh
export A0_ZARA_BINARY=zara
export A0_ZARA_ENDPOINT="ipc:///run/user/$(id -u)/zara.sock"
```

The subprocess uses an argv vector and never invokes a shell. Output is redirected to temporary files and read back with configured bounds, so a noisy child process cannot force an unbounded in-memory capture.

## Enable

Enable `_zara_bridge` from Agent Zero's Plugins UI, or use the normal plugin toggle API. The framework writes a user-level `.toggle-1`, which takes precedence over this plugin's bundled `.toggle-0`.
