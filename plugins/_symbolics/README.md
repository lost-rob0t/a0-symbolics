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

Raw/source checkouts default to `native` unless configured otherwise. The Nix
`a0-symbolics` application and development shell default to `rlm` while no
Symbolics mode has been saved. Once a mode is saved in `_symbolics` settings,
that persisted choice is used on later starts. Those Nix environments also
install and expose the pinned Prolog-RLM package.

The mode can be selected in the `_symbolics` plugin settings or explicitly in
plugin config:

```yaml
mode: rlm
```

The saved setting is applied during the next process startup. Deployments may
override it with:

```sh
A0_SYMBOLICS_MODE=rlm
```

An explicitly supplied environment value has precedence over plugin config.
Invalid modes fail explicitly. RLM mode also fails explicitly if either managed
bundled plugin is missing.

The managed RLM plugins ship disabled at the bundled-root level so native mode
is clean even before startup extensions run. During startup the coordinator
synchronizes their global activation to the selected mode. The transition is
transactional: if a plugin toggle fails, the coordinator reconciles every
managed plugin back to the original activation snapshot and reports incomplete
rollback explicitly. It changes plugin activation only; no Prolog policy is
duplicated in Python.

The Nix integration gate exercises mode transitions from the same writable
runtime layout used by the packaged launcher, including persisted Native mode
and explicit host override precedence. It proves that toggle state lands under
persistent `usr/` rather than the read-only Nix store. The workflow also
requires the committed `flake.lock` to match the exact pinned Prolog-RLM input
before bridge tests or `nix flake check` can pass.
