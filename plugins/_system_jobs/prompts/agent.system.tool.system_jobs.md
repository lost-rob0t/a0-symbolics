### system_jobs
Manage persistent OS-level cron jobs and shell scripts in the a0-symbolics container.

Use this tool only for real system jobs. For Agent Zero prompt/reminder scheduling, use the Agent Zero scheduler instead.

Actions:
- `list` / `status`: inspect configured jobs and cron runtime state.
- `create`: create a job with `name`, five-field cron `schedule` (or standard macro), and `script`; optional absolute `workdir` and `enabled`.
- `update`: replace an existing job by `id` with the complete desired fields.
- `delete`: delete the job identified by `id`.
- `run`: execute the saved job immediately in the background and append output to its persistent log.
- `log`: read recent log output for `id`.
- `sync`: regenerate only the plugin-managed crontab block while preserving unrelated manual crontab entries.

Prefer managed script bodies over complex inline cron commands. Do not create recurring jobs unless the user asked for recurrence. Do not place credentials directly in saved scripts.

Example:
~~~json
{
  "thoughts": ["The user explicitly wants this shell task to run every hour."],
  "headline": "Scheduling system job",
  "tool_name": "system_jobs",
  "tool_args": {
    "action": "create",
    "name": "refresh local index",
    "schedule": "0 * * * *",
    "workdir": "/a0/usr/workdir",
    "enabled": true,
    "script": "./scripts/refresh-index.sh"
  }
}
~~~
