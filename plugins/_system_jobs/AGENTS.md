# System Jobs Plugin DOX

## Purpose

- Own persistent OS-level cron jobs for the a0-symbolics container.
- Provide the same managed jobs through Web UI, agent tool, and plugin skill surfaces.

## Ownership

- `helpers/jobs.py` owns persistent job metadata, managed scripts, logs, crontab rendering, and immediate execution.
- `api/jobs.py` owns Web UI CRUD/run/log/sync operations.
- `tools/system_jobs.py` owns agent-facing job operations.
- `skills/system-jobs/SKILL.md` owns agent workflow guidance.
- `webui/` owns the System Jobs dashboard.
- `extensions/webui/_sidebar-quick-actions-main-start/` owns the sidebar entry point.

## Local Contracts

- Persistent state belongs only under `/a0/usr/system-jobs`.
- The Nix/Home Manager runtime owns the `cron` and `crontab` binaries.
- `/var/cron` is prepared by `docker/symbolics/initialize.sh` as a link into persistent user state.
- Plugin synchronization may replace only the root crontab section between `# BEGIN A0 SYSTEM JOBS` and `# END A0 SYSTEM JOBS`.
- Preserve unrelated manual crontab entries outside the managed block.
- Managed script commands in cron should point to plugin-owned script files; do not inline arbitrary script bodies into crontab command lines.
- Validate ids, schedules, script size, and absolute working directories before writes.
- Do not store credentials or secrets in plugin defaults, docs, or tests.

## Work Guidance

- Keep metadata and script writes atomic where practical.
- Keep the API and agent tool thin over `helpers/jobs.py` so both surfaces behave identically.
- Use A0 notifications for Web UI feedback.
- Prefer background execution for Run Now so long scripts do not block API requests.

## Verification

- Verify five-field cron expressions and supported macros are accepted and malformed schedules are rejected.
- Verify sync preserves unmanaged crontab text and replaces only the managed block.
- Verify create/update writes a persistent script and delete removes its managed script/log.
- Verify the dashboard uses the plugin API and the sidebar opens the dashboard modal.
- In the symbolics image, verify `cron` and `crontab` resolve from `/root/.nix-profile/bin` and the supervised cron process starts.

## Child DOX Index

No child DOX files.
