# scheduler.py DOX

## Purpose

- Own the `scheduler.py` agent tool.
- This module creates, updates, lists, runs, waits for, and deletes scheduled/planned/adhoc tasks.
- Keep this file-level DOX profile synchronized with `scheduler.py` because this directory is intentionally flat.

## Ownership

- `scheduler.py` owns the runtime implementation.
- `scheduler.py.dox.md` owns durable notes about responsibilities, contracts, side effects, and verification for that implementation.
- Classes:
- `SchedulerTool` (`Tool`)
  - `async execute(self, **kwargs)`
  - `async list_tasks(self, **kwargs) -> Response`
  - `async find_task_by_name(self, **kwargs) -> Response`
  - `async show_task(self, **kwargs) -> Response`
  - `async run_task(self, **kwargs) -> Response`
  - `async delete_task(self, **kwargs) -> Response`
  - `async update_task(self, **kwargs) -> Response`
  - `async create_scheduled_task(self, **kwargs) -> Response`
  - `def _apply_task_kb_settings(self, task, kwargs: dict) -> Response | None`
    - Shared by `create_scheduled_task`, `create_adhoc_task`, and `create_planned_task`.
    - Validates and applies `task_kb` (list of strings), `max_run_contexts` (int >= 1),
      `agent_profile` (non-empty string or null), and `model_override`
      (non-empty object, bare preset-name string, or null) onto a freshly created task.
- `update_task` also accepts `task_kb` (wholesale replacement), `max_run_contexts`,
  `agent_profile`, and `model_override` (same shapes as create; `null` clears the override).
- `delete_task` removes the legacy task context plus every persisted run context listed in
  `task.run_context_ids` (historical run chats for this task).
- Top-level functions:
- `_current_action(tool: Tool, kwargs: dict) -> str`
- `_normalize_timezone(value: Any) -> str | None`
- `_schedule_timezone(kwargs: dict) -> str | None`
- `_task_schedule_from_input(schedule: Any, timezone: str | None=...) -> TaskSchedule`
- `_validate_task_schedule(task_schedule: TaskSchedule) -> str`
- `_task_plan_from_input(plan: Any) -> tuple[TaskPlan | None, str]`
- Notable constants/configuration names: `DEFAULT_WAIT_TIMEOUT`, `LOCAL_TIMEZONE_ALIASES`.

## Runtime Contracts

- Tool modules must define `helpers.tool.Tool` subclasses and return `helpers.tool.Response` from `execute(...)`.
- Update this file whenever tool arguments, output shape, `break_loop` behavior, intervention handling, prompt instructions, or side effects change.
- `SchedulerTool` is a `Tool`.
- `SchedulerTool` defines `execute(...)`.
- Scheduler runs always execute in a fresh per-occurrence context, so starting or waiting for a task never aliases or terminates the caller's chat. Deletion cancels the current run context while retaining independently persisted historical run chats.
- Observed side-effect areas: filesystem writes, filesystem deletion, settings/state persistence, secret handling, scheduler state.
- Imported dependency areas include: `agent`, `asyncio`, `datetime`, `helpers`, `helpers.localization`, `helpers.projects`, `helpers.task_scheduler`, `helpers.tool`, `json`, `pytz`, `random`, `re`, `typing`.

## Key Concepts

- Important called helpers/classes observed in the source: `str.strip.lower.replace`, `str.strip`, `_normalize_timezone`, `TaskSchedule`, `task_schedule.to_crontab`, `timezone_name.lower`, `Localization.get.get_timezone`, `pytz.timezone`, `schedule.split`, `re.match`, `parse_datetime`, `TaskPlan.create`, `_current_action`, `get_context_project_name`, `TaskScheduler.get.get_tasks`, `Response`, `TaskScheduler.get.find_task_by_name`, `TaskScheduler.get.get_task_by_uuid`, `scheduler.get_task_by_uuid`, `self._resolve_project_metadata`.
- Keep request/response, tool, or helper semantics documented here at the same time as source changes.

## Work Guidance

- Keep tool output concise, model-readable, and safe for history persistence.
- Coordinate argument or behavior changes with prompt tool instructions and skill guidance.
- Respect intervention flow for long-running, external, or user-visible operations.

## Verification

- Run targeted tool and prompt-contract tests for changed behavior; smoke-test agent execution when no focused test exists.
- Related tests observed by source search:
  - `tests/test_task_scheduler_timezone.py`
  - `tests/test_timezone_regressions.py`
  - `tests/test_tool_action_contracts.py`
  - `tests/test_tool_request_normalization.py`

## Child DOX Index

No child DOX files.
