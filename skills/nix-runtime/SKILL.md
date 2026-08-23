---
name: nix-runtime
description: Use for installing or changing persistent CLI tooling in a0-symbolics with Nix/Home Manager, inspecting the persistent Nix environment, or repairing the Home Manager profile.
triggers:
  - "nix"
  - "home manager"
  - "home-manager"
  - "install package"
  - "persistent package"
  - "nix profile"
  - "nix shell"
allowed_tools:
  - code_execution_tool
---

# a0-symbolics Nix Runtime

The a0-symbolics container intentionally persists only `/nix` and `/a0/usr`. Treat Home Manager as the durable package/config layer and the Docker image as the replaceable Agent Zero application layer.

## Persistent paths

- Home Manager flake: `/a0/usr/home-manager/flake.nix`
- Home Manager package/config module: `/a0/usr/home-manager/home.nix`
- Pinned inputs: `/a0/usr/home-manager/flake.lock`
- Persistent Nix store and profiles: `/nix`
- Persistent Agent Zero user data: `/a0/usr`

Do not create a persistent mount for `/a0` or application source. That would mask image updates.

## Durable package installs

For a package the user wants available after future container rebuilds:

1. Inspect `/a0/usr/home-manager/home.nix`.
2. Confirm the package attribute with Nix when uncertain. Prefer `nix search nixpkgs# <name>` or a temporary `nix shell nixpkgs#<attr> -c <cmd> --version` probe.
3. Add the package attribute to `home.packages` in `home.nix`.
4. Detect the flake output name:

```bash
case "$(uname -m)" in
  x86_64) hm_system=x86_64-linux ;;
  aarch64|arm64) hm_system=aarch64-linux ;;
  *) echo "unsupported architecture" >&2; exit 1 ;;
esac
```

5. Apply it:

```bash
cd /a0/usr/home-manager
home-manager switch --flake ".#root-${hm_system}"
```

6. Verify the requested binary resolves from `/root/.nix-profile/bin` and run its version/help command.

Prefer this flow over `apt install`, `pip install --user`, global npm installs, or ad-hoc `nix profile install` for durable system tooling.

## Temporary tools

For one-off tooling that should not become part of the persistent profile, prefer:

```bash
nix shell nixpkgs#<package> -c <command>
```

or:

```bash
nix run nixpkgs#<package> -- <args>
```

Do not add every transient dependency to Home Manager.

## Updating pinned inputs

The persisted `flake.lock` intentionally keeps rebuilds reproducible. Do not run `nix flake update` just because a newer package exists. Update inputs only when the user explicitly wants the Home Manager/Nixpkgs baseline advanced or when a required package fix demands it.

After an intentional update, run Home Manager switch and verify the affected tools before reporting success.

## Cron and System Jobs

- The durable cron package is `pkgs.cron` in Home Manager.
- The symbolics initializer runs `/root/.nix-profile/bin/cron -n` through Agent Zero's existing supervisor slot.
- `/var/cron` points into `/a0/usr/system-jobs/cron`, so `crontab` survives container replacement.
- For jobs that should be visible and manageable in the Web UI, load the `system-jobs` skill and use the `system_jobs` tool instead of hand-editing its managed crontab block.

## Guardrails

- Never store secrets in the Home Manager flake or committed default profile.
- Preserve the persisted user's `home.nix` during image updates; the image seed is only for first boot.
- Do not replace the user's `flake.lock` during normal startup.
- Do not garbage-collect the Nix store aggressively unless the user explicitly asks; `/nix` is shared persistent state for this Agent Zero instance.
