# Symbolics Docker DOX

## Purpose

- Own the local a0-symbolics Docker wrapper, its persistent Nix store, and its reusable Home Manager seed.
- Keep Agent Zero application code image-owned so container replacement and updates do not depend on a persistent `/a0` tree.

## Ownership

- `compose.yml` owns the local a0-symbolics service and its two persistent volumes.
- `initialize.sh` seeds and activates the Home Manager profile before normal Agent Zero startup.
- `home-manager/` owns the default reusable Home Manager configuration copied into user state on first boot.

## Local Contracts

- Persist only `/nix` and `/a0/usr`; do not persist the full `/a0` application tree.
- Store the mutable Home Manager configuration under `/a0/usr/home-manager` so it survives container replacement without making application code persistent.
- Treat the committed Home Manager files as first-boot defaults only. Never overwrite a user's persisted Home Manager configuration during later starts.
- Keep Nix daemonless inside the container and enable flakes with sandboxing disabled for container compatibility.
- Never bake secrets or local user data into the image.

## Work Guidance

- Keep the wrapper thin: prepare Nix/Home Manager, then exec the normal `/exe/initialize.sh` entrypoint.
- Prefer adding reusable CLI tooling to `home-manager/home.nix` rather than apt-installing it into the image.
- Image/runtime updates must remain safe with an existing `a0-symbolics-nix` and `a0-symbolics-usr` volume.

## Verification

- Build with `docker compose -f docker/symbolics/compose.yml build`.
- Start once, confirm Home Manager activation, recreate the container, and confirm the same `/nix` store and `/a0/usr/home-manager/flake.lock` are reused.
- Confirm the compose file has exactly two persistent mounts: `/nix` and `/a0/usr`.

## Child DOX Index

No child DOX files.
