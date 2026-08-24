# Symbolics Runtime

`_symbolics` is the single runtime-mode coordinator for this Agent Zero fork.
It keeps the stock Agent Zero path and the Prolog-RLM path mutually exclusive
at plugin activation time instead of letting two context/tool control planes run
at once.

## Modes

- `native`: disables `_prolog_rlm` and `_prolog_context_compiler`. Agent Zero
  runs its native prompt, skill, tool, memory, and context behavior.
- `rlm`: enables `_prolog_rlm` and `_prolog_context_compiler` together. Agent
  Zero remains the host/UI/tool implementation while Prolog-RLM owns symbolic
  context selection, prompt compilation, budgeting, planning, authority/effect
  reasoning, supervision, and verification through the existing typed bridge.

The default remains `native` until the full installed-package/Nix/live-provider
production gate is green. Select RLM mode with either the plugin config:

```yaml
mode: rlm
```

or the process environment override:

```sh
A0_SYMBOLICS_MODE=rlm
```

The environment value has precedence over plugin config. Invalid modes fail
explicitly. RLM mode also fails explicitly if either managed bundled plugin is
missing.

The managed RLM plugins ship disabled at the bundled-root level so native mode
is clean even before startup extensions run. During startup the coordinator
synchronizes their global activation to the selected mode. It changes plugin
activation only; no Prolog policy is duplicated in Python.
