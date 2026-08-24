# Symbolics Runtime DOX

## Purpose

- Own the single runtime-mode switch for this fork.
- Keep native Agent Zero and the paired Prolog-RLM control plane mutually exclusive.

## Ownership

- `default_config.yaml` owns the source-checkout default runtime mode.
- `webui/config.html` exposes the saved runtime-mode selector.
- `helpers/mode.py` owns mode resolution and paired plugin activation.
- `extensions/python/startup_migration/` applies the selected mode before normal prompt work.
- `tests/` owns deterministic mode-switch contracts.
- Root `flake.nix` owns the packaged RLM default and writable-runtime integration smoke.

## Local Contracts

- Supported modes are exactly `native` and `rlm`.
- `A0_SYMBOLICS_MODE` overrides plugin config for host-controlled deployment.
- Raw/source checkout defaults to `native`; the Nix application/dev shell may default to `rlm` only while they provide the pinned Prolog-RLM package and exact-head integration gates.
- Native mode disables `_prolog_rlm` and `_prolog_context_compiler` together.
- RLM mode enables both together; do not permit a half-enabled symbolic control plane.
- Project/profile activation overrides for either managed RLM plugin must not contradict the selected Symbolics mode. A conflicting scoped toggle fails startup before any global mode mutation rather than silently permitting a half control plane or deleting scoped/source-owned state.
- Failed transitions must reconcile every managed plugin to the full original activation snapshot, including a toggle that raises after writing state. Incomplete rollback is an explicit failure.
- This coordinator may change plugin activation only. Do not copy Prolog-RLM selection, budgeting, authority, planning, or verification policy into Python.
- Invalid mode values and missing managed plugins in RLM mode fail explicitly.
- Saved UI/config mode changes take effect on process startup; do not imply an in-process hot swap unless worker shutdown/state handoff is explicitly implemented and tested.

## Work Guidance

- Prefer adding behavior to the paired RLM plugins or Prolog-RLM itself rather than growing this coordinator.
- Keep mode transitions deterministic and reversible.
- Do not add a second context, memory, tool-selection, or authority implementation here.
- Keep the committed Prolog-RLM flake lock consistent with the explicit input revision; CI must fail on lock drift rather than silently accepting a regenerated workspace lock.

## Verification

- Run `pytest plugins/_symbolics/tests`.
- Verify native mode excludes both RLM plugins from the enabled-plugin set.
- Verify RLM mode enables both and the existing context/runtime plugin suites pass.
- Verify conflicting project/profile activation overrides fail before root toggle mutation.
- Verify the Nix runtime-layout check writes mode state only through the writable `usr/` path and can transition RLM -> native cleanly.
- Require exact-head installed-package/Nix and applicable real-provider evidence before promoting a wider production default.

## Child DOX Index

No child DOX files.
