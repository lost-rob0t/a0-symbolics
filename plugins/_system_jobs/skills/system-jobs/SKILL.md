---
name: system-jobs
description: Use when the user wants a real OS cron job, recurring shell script, persistent crontab entry, or to inspect/run System Jobs managed by a0-symbolics.
triggers:
  - "system job"
  - "cron job"
  - "crontab"
  - "schedule script"
  - "run this script every"
  - "system-jobs"
allowed_tools:
  - system_jobs
  - code_execution_tool
---

# System Jobs

Use the `system_jobs` tool for persistent OS-level jobs. These are real cron jobs inside the Agent Zero container, not Agent Zero scheduler prompts.

## Storage and runtime

- Job metadata: `/a0/usr/system-jobs/jobs.json`
- Managed scripts: `/a0/usr/system-jobs/scripts/`
- Job logs: `/a0/usr/system-jobs/logs/`
- Persistent Vixie cron state: `/a0/usr/system-jobs/cron/`, exposed at `/var/cron`
- Cron and `crontab` come from the persistent Home Manager profile under `/root/.nix-profile/bin/`.
- `/a0/usr` and `/nix` persist across container replacement; application code does not.

## Tool actions

- `list` / `status`: inspect jobs and cron runtime.
- `create`: requires `name`, `schedule`, and `script`; optional `workdir`, `enabled`.
- `update`: requires the existing `id` plus the complete desired job fields.
- `delete`: requires `id`.
- `run`: run a saved script immediately and append output to its log.
- `log`: read recent saved output.
- `sync`: regenerate the managed crontab block without touching unrelated manual entries.

## Rules

- Prefer `system_jobs` over directly editing root's crontab when the job should appear in the System Jobs Web UI.
- Use a five-field cron expression such as `0 2 * * *`, or a standard macro such as `@hourly` or `@daily`.
- The working directory must be an absolute container path. Default to `/a0/usr/workdir` when no project path is specified.
- Put the actual task in the managed script body rather than stuffing complex shell into the cron expression.
- Do not silently schedule a job merely because a command might benefit from recurrence. Create or change jobs only when the user asks.
- Before destructive changes, list jobs and identify the target by id.
- Use `run` only when the user asks to execute now or when verification of a newly created harmless job is clearly part of the requested setup.
- Do not put API keys or secrets directly in job script bodies. Prefer files/environment managed outside the job definition.

## Raw crontab

Manual `crontab` use is supported and persistent because `/var/cron` lives under `/a0/usr/system-jobs/cron`. The System Jobs plugin owns only the block between:

```text
# BEGIN A0 SYSTEM JOBS
# END A0 SYSTEM JOBS
```

Do not manually edit inside that block; plugin sync will replace it. Unmanaged lines outside the block are preserved.
