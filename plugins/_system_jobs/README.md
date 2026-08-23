# System Jobs

System Jobs adds persistent, real cron-backed script scheduling to the a0-symbolics Agent Zero image.

It is intentionally separate from Agent Zero's built-in scheduler: the built-in scheduler runs agent prompts, while System Jobs runs operating-system scripts and commands through Vixie cron.

## Persistence

The symbolics runtime persists only `/nix` and `/a0/usr`. System Jobs stores everything under `/a0/usr/system-jobs`:

- `jobs.json` — managed job metadata and script bodies
- `scripts/` — generated executable shell scripts
- `logs/` — stdout/stderr from scheduled and Run Now executions
- `cron/` — the persistent Nix Vixie cron spool, linked to `/var/cron`

Because the cron spool itself is persistent, ordinary root `crontab` entries also survive container replacement. System Jobs only rewrites its own marked block and preserves unrelated lines.

## Web UI

Use the **schedule** icon in the Agent Zero sidebar to open System Jobs. The dashboard can:

- create and edit scheduled scripts;
- use five-field cron expressions or standard cron macros;
- enable or disable jobs;
- run a saved script immediately;
- view recent logs;
- delete jobs;
- force the managed crontab block to resync.

## Agent tool

The bundled `system-jobs` skill exposes the `system_jobs` tool with `list`, `status`, `create`, `update`, `delete`, `run`, `log`, and `sync` actions.

## Nix runtime

`cron` is installed through `/a0/usr/home-manager/home.nix`. The symbolics initializer swaps Agent Zero's existing supervised cron slot to `/root/.nix-profile/bin/cron -n`, so there is still only one cron daemon in the container.
