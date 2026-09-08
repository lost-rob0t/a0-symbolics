### scheduler
Manage saved tasks and schedules. For complex task work, load skill `scheduled-tasks`.

Actions: `list_tasks`, `find_task_by_name`, `show_task`, `run_task`, `update_task`, `delete_task`, `create_scheduled_task`, `create_adhoc_task`, `create_planned_task`, `wait_for_task`.

Common args: `action`, `name`, `uuid`, `system_prompt`, `prompt`, `attachments`, `schedule`, `timezone`, `plan`, `dedicated_context`, `task_kb`, `max_run_contexts`, `agent_profile`, `model_override`.

Task knowledge base and run bindings:
- `task_kb`: list of durable knowledge strings for the task, injected into every run prompt. Use for stable facts, conventions, and handoff notes that must survive across runs.
- `max_run_contexts`: how many historical run chats to keep persisted for this task (default 10). Each run gets a fresh context; oldest run chats beyond this bound are deleted.
- `agent_profile`: agent profile name (e.g. `mara`, `developer`) used by task runs; omit to use the global default profile.
- `model_override`: per-chat model override for runs, either a preset name string (e.g. `model_override: "Efficiency"`) or an object (`{"preset_name": "...", "chat": {...}}`); set to `null` to clear.

Rules:
- Before `create_*`, `update_task`, `delete_task`, or `run_task`, inspect existing tasks with `find_task_by_name` or `list_tasks`.
- Do not run scheduled/planned tasks unless the user asks to run now.
- Do not create recursive task prompts that schedule more tasks.
- New tasks use a dedicated context unless `dedicated_context` is `false`.
- Use `create_scheduled_task` for recurring/cron tasks; `schedule` must be cron fields, not an ISO datetime.
- For one planned date/time, use `create_planned_task` with `plan: ["YYYY-MM-DDTHH:MM:SS"]`.
- Use IANA timezones like `Europe/Rome`; include timezone when the user names a timezone.
- For "tomorrow at 9:15 Rome time", scheduled shape is `schedule: {"minute":"15","hour":"9","day":"11","month":"5","weekday":"*","timezone":"Europe/Rome"}`.
