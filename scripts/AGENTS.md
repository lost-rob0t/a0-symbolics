# Scripts DOX

## Purpose

- Own maintainer and automation scripts that live outside GitHub workflow directories.
- Keep scripts deterministic, documented by nearby callers, and safe to run in clean checkouts.

## Ownership

- `openrouter_release_notes_system_prompt.md` is consumed by `.github/scripts/docker_release_plan.py`.
- `symbolics` owns bounded local Symbolics build, launch, status, and verification behavior; the small command wrappers delegate to it.
- `forgejo-runner/` owns the CI runner deploy kit: `config.template.yml` (authoritative labels, capacity 1, 3h timeout) and `deploy.sh` (repo-scoped registration, systemd --user unit, declared-labels verification). The runbook lives in `docs/forgejo-runner-deploy.md`.
- Additional repository maintenance scripts belong here when they are not runtime application code.

## Local Contracts

- Do not commit secrets, generated credentials, private release notes, or local machine paths.
- Scripts used by CI must have stable inputs and fail with actionable errors.
- Keep script behavior synchronized with `.github/AGENTS.md`, workflow YAML, and tests.
- Runner registration must be repository-scoped: user-scoped runners never receive dispatched tasks.
- Runner labels live in `config.template.yml`; the `nix` label is host-executor only (docker containers cannot sandbox nix builds), and `capacity` stays at 1.

## Work Guidance

- Prefer standard library Python or simple shell-compatible assets unless a dependency already exists for the script's runtime.
- Keep prompts and automation inputs concise and version-controlled.
- Update callers when renaming or moving scripts.

## Verification

- Run targeted tests for any automation script with coverage.
- For release-note prompt changes, inspect generated output format expectations in `.github/scripts/docker_release_plan.py`.

## Child DOX Index

No child DOX files.
