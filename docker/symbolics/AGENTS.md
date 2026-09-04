# Symbolics Docker DOX

## Purpose

- Own the local a0-symbolics Docker wrapper, its persistent Nix store, and its reusable Home Manager seed.
- Keep Agent Zero application code image-owned so container replacement and updates do not depend on a persistent `/a0` tree.

## Ownership

- `compose.yml.example` owns the tracked example for the local a0-symbolics service and its two persistent volumes.
- `compose.yml` is machine-local, copied from the example, and intentionally gitignored so host-specific changes survive pulls.
- `initialize.sh` seeds and activates the Home Manager profile before normal Agent Zero startup.
- `healthcheck.sh` and `smoke.*` own live Agent Zero-to-Prolog readiness evidence.
- `home-manager/` owns the default reusable Home Manager configuration copied into user state on first boot.

## Local Contracts

- Persist only `/nix` and `/a0/usr`; do not persist the full `/a0` application tree.
- Store the mutable Home Manager configuration under `/a0/usr/home-manager` so it survives container replacement without making application code persistent.
- Treat the committed Home Manager files as first-boot defaults only. Never overwrite a user's persisted Home Manager configuration during later starts.
- Keep Nix daemonless inside the container and enable flakes with sandboxing disabled for container compatibility.
- Bound both image builds and the running service to 8 GiB by default; local operators may choose a different explicit build limit.
- Bound in-container nix builds with bounded parallelism derived from the same memory reality: `initialize.sh` derives `max-jobs`/`cores` from the container cgroup limit and writes them into `/etc/nix/nix.conf`, preserving the image-owned settings. Never rely on nix's default per-host parallelism inside a memory-capped container; operators override with `A0_NIX_MAX_JOBS`, `A0_NIX_CORES`, or `~/.config/nix/nix.conf`.
- Generate smoke evidence for the container lifetime: `generate_smoke_evidence` retries until readiness and keeps refreshing `/run/a0-symbolics/smoke.json` (default every 30 s, `A0_SMOKE_REFRESH_SECONDS`). A one-shot boot window can permanently starve `healthcheck.sh` after a slow start or crash loop.
- Treat any non-running supervised process as unhealthy; HTTP and cached smoke evidence alone are insufficient readiness evidence.
- Never bake secrets or local user data into the image.
- Never track `docker/symbolics/compose.yml`; local ports, mounts, devices, and machine-specific overrides belong there.

## Work Guidance

- Keep the wrapper thin: prepare Nix/Home Manager, then exec the normal `/exe/initialize.sh` entrypoint.
- Prefer adding reusable CLI tooling to `home-manager/home.nix` rather than apt-installing it into the image.
- Image/runtime updates must remain safe with an existing `a0-symbolics-nix` and `a0-symbolics-usr` volume.
- When the example changes, document whether existing local compose files need a manual merge.

## Verification

- Copy `docker/symbolics/compose.yml.example` to `docker/symbolics/compose.yml` before local use.
- Build with `docker compose -f docker/symbolics/compose.yml build`.
- Start once, confirm Home Manager activation, recreate the container, and confirm the same `/nix` store and `/a0/usr/home-manager/flake.lock` are reused.
- Confirm the example compose file has exactly two persistent mounts: `/nix` and `/a0/usr`.
- Confirm `git check-ignore docker/symbolics/compose.yml` succeeds.
- Run `pytest tests/test_symbolics_live_api.py` with `A0_SYMBOLICS_URL` set to the published HTTP URL to exercise the live UI and `/api/health` route.
- Run `pytest tests/test_symbolics_docker.py` after changing `initialize.sh`, `healthcheck.sh`, or the compose example; it asserts the bounded-nix, smoke-refresh, and supervisor-readiness contracts.

## Child DOX Index

No child DOX files.
