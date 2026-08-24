# Symbolics Runtime DOX

## Purpose

- Own the single runtime-mode switch for this fork.
- Keep native Agent Zero and the paired Prolog-RLM control plane mutually exclusive.

## Ownership

- `default_config.yaml` owns the default runtime mode.
- `helpers/mode.py` owns mode resolution and paired plugin activation.
- `extensions/python/startup_migration/` applies the selected mode before normal prompt work.
- `tests/` owns deterministic mode-switch contracts.

## Local Contracts

- Supported modes are exactly `native` and `rlm`.
- `A0_SYMBOLICS_MODE` overrides plugin config for host-controlled deployment.
- Native mode disables `_prolog_rlm` and `_prolog_context_compiler` together.
- RLM mode enables both together; do not permit a half-enabled symbolic control plane.
- This coordinator may change plugin activation only. Do not copy Prolog-RLM selection, budgeting, authority, planning, or verification policy into Python.
- Invalid mode values and missing managed plugins in RLM mode fail explicitly.

## Work Guidance

- Prefer adding behavior to the paired RLM plugins or Prolog-RLM itself rather than growing this coordinator.
- Keep mode transitions deterministic and reversible.
- Do not add a second context, memory, tool-selection, or authority implementation here.

## Verification

- Run `pytest plugins/_symbolics/tests`.
- Verify native mode excludes both RLM plugins from the enabled-plugin set.
- Verify RLM mode enables both and the existing context/runtime plugin suites pass.
- Before changing the default to `rlm`, require the installed-package, Nix/container, and live-provider production gates to pass on the exact candidate head.

## Child DOX Index

No child DOX files.
