import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers import task_scheduler
from helpers import state_monitor_integration
from helpers.task_scheduler import (
    AdHocTask,
    SchedulerTaskList,
    TaskRunStatus,
    TaskScheduler,
    TaskState,
    bound_previous_run_output,
    deserialize_task,
    record_scheduler_terminal_response,
    serialize_task,
)


class MemoryTaskList:
    def __init__(self, task):
        self.tasks = [task]

    async def reload(self):
        return self

    async def save(self):
        return self

    async def update_task_by_uuid(self, task_uuid, updater, verify=lambda task: True):
        task = next(
            (
                candidate
                for candidate in self.tasks
                if candidate.uuid == task_uuid and verify(candidate)
            ),
            None,
        )
        if task is None:
            return None
        updater(task)
        return task

    def get_task_by_uuid(self, task_uuid):
        return next((task for task in self.tasks if task.uuid == task_uuid), None)

    def get_task_by_run_id(self, run_id):
        return next(
            (
                task
                for task in self.tasks
                if run_id
                in {task.current_run_id, task.last_run_id, task.previous_run_id}
            ),
            None,
        )


class FakeLog:
    def __init__(self):
        self.entries = []

    def log(self, **entry):
        self.entries.append(entry)
        return SimpleNamespace(id=entry.get("id", ""))


class FakeAgent:
    behaviors = []

    def __init__(self, context):
        self.context = context
        self.history = []
        self.data = {}

    def hist_add_user_message(self, message):
        self.history.append(message)

    async def monologue(self):
        kind, value = self.behaviors.pop(0)
        if kind == "success":
            response = SimpleNamespace(message=value, break_loop=True)
            record_scheduler_terminal_response(self, "response", response)
            return value
        if kind == "raw":
            return value
        if kind == "timeout":
            raise TimeoutError(value)
        if kind == "cancel":
            raise asyncio.CancelledError()
        raise RuntimeError(value)


class FakeAgentContext:
    contexts = {}
    current_id = None

    def __init__(self, _config, id, name, type=None, data=None, **_kwargs):
        self.id = id
        self.name = name
        self.type = type
        self.data = data or {}
        self.log = FakeLog()
        self.streaming_agent = None
        self.agent0 = FakeAgent(self)
        self.__class__.contexts[id] = self

    @classmethod
    def get(cls, context_id):
        return cls.contexts.get(context_id)

    @classmethod
    def use(cls, context_id):
        cls.current_id = context_id
        return cls.get(context_id)

    def get_data(self, key, recursive=True):
        return self.data.get(key)

    def set_data(self, key, value, recursive=True):
        self.data[key] = value


class QuietPrinter:
    def print(self, *_args, **_kwargs):
        pass


@pytest.fixture
def scheduler_runtime(monkeypatch):
    task = AdHocTask.create(
        name="fresh task",
        system_prompt="scheduler system",
        prompt="do the current work",
        token="123",
    )
    scheduler = object.__new__(TaskScheduler)
    scheduler._tasks = MemoryTaskList(task)
    scheduler._printer = QuietPrinter()
    scheduler._running_deferred_tasks = {}
    scheduler._running_tasks_lock = task_scheduler.threading.RLock()

    FakeAgent.behaviors = []
    FakeAgentContext.contexts = {}
    FakeAgentContext.current_id = None
    saved_contexts = []

    async def no_finish(self):
        return None

    monkeypatch.setattr(task_scheduler, "AgentContext", FakeAgentContext)
    monkeypatch.setattr(task_scheduler, "initialize_agent", lambda: object())
    monkeypatch.setattr(
        task_scheduler,
        "save_tmp_chat",
        lambda context: saved_contexts.append(context.id),
    )
    monkeypatch.setattr(task_scheduler.projects, "activate_project", lambda *_args: None)
    monkeypatch.setattr(task_scheduler.BaseTask, "on_finish", no_finish)
    monkeypatch.setattr(
        state_monitor_integration,
        "mark_dirty_all",
        lambda **_kwargs: None,
    )
    return scheduler, task, saved_contexts


def run_occurrence(scheduler, task, run_id):
    asyncio.run(scheduler._execute_task(task.uuid, run_id))


def test_successive_occurrences_use_fresh_context_and_explicit_previous_result(
    scheduler_runtime,
):
    scheduler, task, saved_contexts = scheduler_runtime
    FakeAgent.behaviors = [("success", "first terminal"), ("success", "second terminal")]

    run_occurrence(scheduler, task, "run-1")
    run_occurrence(scheduler, task, "run-2")

    first = FakeAgentContext.contexts["run-1"]
    second = FakeAgentContext.contexts["run-2"]
    assert first is not second
    assert first.agent0 is not second.agent0
    assert first.agent0.data == second.agent0.data == {}
    assert len(first.agent0.history) == len(second.agent0.history) == 1
    assert "Previous run result" not in first.agent0.history[0].message
    assert "first terminal" in second.agent0.history[0].message
    assert "second terminal" not in second.agent0.history[0].message
    assert second.agent0.history[0].system_message == ["scheduler system"]
    assert first.data["scheduler_run"] == {
        "task_id": task.uuid,
        "run_id": "run-1",
    }
    assert task.current_run_id is None
    assert task.last_run_id == "run-2"
    assert task.previous_run_id == "run-2"
    assert task.previous_run_output == "second terminal"
    assert task.last_run_status == TaskRunStatus.SUCCEEDED
    assert {"run-1", "run-2"}.issubset(saved_contexts)


def test_failed_run_does_not_poison_last_successful_handoff(scheduler_runtime):
    scheduler, task, _saved_contexts = scheduler_runtime
    FakeAgent.behaviors = [
        ("success", "known good"),
        ("error", "provider failed"),
        ("success", "recovered"),
    ]

    run_occurrence(scheduler, task, "run-good")
    run_occurrence(scheduler, task, "run-failed")
    assert task.previous_run_id == "run-good"
    assert task.previous_run_output == "known good"
    assert task.last_run_status == TaskRunStatus.FAILED

    task.state = TaskState.IDLE
    run_occurrence(scheduler, task, "run-recovered")
    recovered_prompt = FakeAgentContext.contexts["run-recovered"].agent0.history[0].message
    assert "known good" in recovered_prompt
    assert "provider failed" not in recovered_prompt
    assert task.previous_run_output == "recovered"


@pytest.mark.parametrize(
    ("behavior", "expected_status", "expected_state"),
    [
        (("raw", '{"tool_name":"exec","tool_args":{}}'), TaskRunStatus.FAILED, TaskState.ERROR),
        (("timeout", "blocked model phase"), TaskRunStatus.TIMED_OUT, TaskState.ERROR),
    ],
)
def test_nonterminal_and_timeout_results_are_not_promoted(
    scheduler_runtime,
    behavior,
    expected_status,
    expected_state,
):
    scheduler, task, _saved_contexts = scheduler_runtime
    task.previous_run_id = "older-success"
    task.previous_run_output = "keep me"
    FakeAgent.behaviors = [behavior]

    run_occurrence(scheduler, task, "bad-run")

    assert task.last_run_status == expected_status
    assert task.state == expected_state
    assert task.previous_run_id == "older-success"
    assert task.previous_run_output == "keep me"


def test_cancelled_run_is_recorded_without_replacing_success(scheduler_runtime):
    scheduler, task, _saved_contexts = scheduler_runtime
    task.previous_run_id = "older-success"
    task.previous_run_output = "keep me"
    FakeAgent.behaviors = [("cancel", None)]

    with pytest.raises(asyncio.CancelledError):
        run_occurrence(scheduler, task, "cancelled-run")

    assert task.state == TaskState.IDLE
    assert task.last_run_status == TaskRunStatus.CANCELLED
    assert task.previous_run_id == "older-success"
    assert task.previous_run_output == "keep me"


def test_older_completion_cannot_overwrite_newer_run(scheduler_runtime):
    scheduler, task, _saved_contexts = scheduler_runtime
    task.current_run_id = "newer-run"
    task.last_run_id = "newer-run"
    task.last_run_status = TaskRunStatus.RUNNING
    task.previous_run_id = "known-good"
    task.previous_run_output = "known output"

    updated = asyncio.run(
        scheduler._finish_run(
            task.uuid,
            "older-run",
            TaskRunStatus.SUCCEEDED,
            "stale output",
        )
    )

    assert updated is None
    assert task.current_run_id == "newer-run"
    assert task.previous_run_id == "known-good"
    assert task.previous_run_output == "known output"


def test_concurrent_start_cannot_replace_active_run_handle(scheduler_runtime):
    scheduler, task, _saved_contexts = scheduler_runtime
    first = SimpleNamespace()
    second = SimpleNamespace()

    assert scheduler._register_running_task(task.uuid, first) is True
    assert scheduler._register_running_task(task.uuid, second) is False
    assert scheduler._running_deferred_tasks[task.uuid] is first


def test_task_lookup_finds_current_and_historical_run_ids(scheduler_runtime):
    scheduler, task, _saved_contexts = scheduler_runtime
    task.current_run_id = "current-run"
    task.last_run_id = "last-run"
    task.previous_run_id = "successful-run"

    for run_id in ("current-run", "last-run", "successful-run"):
        assert scheduler.get_task_by_run_id(run_id) is task
    assert scheduler.get_task_by_run_id("unknown-run") is None


def test_output_handoff_is_utf8_bounded_with_full_digest_and_run_link(
    scheduler_runtime,
):
    scheduler, task, _saved_contexts = scheduler_runtime
    output = "start-" + ("é" * 20)
    bounded, digest, output_bytes, truncated = bound_previous_run_output(output, 17)

    assert len(bounded.encode("utf-8")) <= 17
    assert output.startswith(bounded)
    assert digest == hashlib.sha256(output.encode("utf-8")).hexdigest()
    assert output_bytes == len(output.encode("utf-8"))
    assert truncated is True

    task.previous_run_output_limit_bytes = 17
    task.current_run_id = "bounded-run"
    asyncio.run(
        scheduler._finish_run(
            task.uuid,
            "bounded-run",
            TaskRunStatus.SUCCEEDED,
            output,
        )
    )
    previous = json.loads(
        task_scheduler.build_task_prompt(task).split(
            "## Previous run result:\n", 1
        )[1]
    )
    assert previous["run_id"] == previous["full_run_context_id"] == "bounded-run"
    assert previous["output"] == bounded
    assert previous["sha256"] == digest
    assert previous["full_output_bytes"] == output_bytes
    assert previous["truncated"] is True


def test_persisted_task_migration_and_restart_recovery_preserve_run_metadata():
    legacy = deserialize_task(
        {
            "type": "adhoc",
            "uuid": "durable-task",
            "name": "legacy",
            "system_prompt": "system",
            "prompt": "prompt",
            "token": "123",
        }
    )
    assert legacy.context_id == "durable-task"
    assert legacy.last_run_status == TaskRunStatus.NEVER
    assert legacy.previous_run_output is None

    legacy.last_run_id = "run-before-restart"
    legacy.last_run_status = TaskRunStatus.SUCCEEDED
    legacy.previous_run_id = "run-before-restart"
    legacy.previous_run_output = "restart-safe output"
    legacy.previous_run_output_sha256 = hashlib.sha256(
        b"restart-safe output"
    ).hexdigest()
    legacy.previous_run_output_bytes = len(b"restart-safe output")

    payload = SchedulerTaskList(tasks=[legacy]).model_dump_json()
    restored = SchedulerTaskList.model_validate_json(payload).tasks[0]
    serialized = serialize_task(restored)
    prompt = task_scheduler.build_task_prompt(restored)

    assert serialized["uuid"] == "durable-task"
    assert serialized["last_run_id"] == "run-before-restart"
    assert serialized["last_run_status"] == TaskRunStatus.SUCCEEDED
    assert serialized["previous_run_output"] == "restart-safe output"
    assert json.loads(prompt.split("## Previous run result:\n", 1)[1])["output"] == "restart-safe output"


def test_terminal_attestation_rejects_nonresponse_empty_and_nonbreaking_tools():
    context = FakeAgentContext(
        object(),
        id="run",
        name="run",
        data={"scheduler_run": {"task_id": "task", "run_id": "run"}},
    )
    agent = context.agent0

    record_scheduler_terminal_response(
        agent, "exec", SimpleNamespace(message="raw tool output", break_loop=True)
    )
    record_scheduler_terminal_response(
        agent, "response", SimpleNamespace(message="", break_loop=True)
    )
    record_scheduler_terminal_response(
        agent, "response", SimpleNamespace(message="progress", break_loop=False)
    )
    assert context.get_data(task_scheduler.SCHEDULER_TERMINAL_RESULT_KEY) is None

    record_scheduler_terminal_response(
        agent, "response", SimpleNamespace(message="terminal", break_loop=True)
    )
    assert context.get_data(task_scheduler.SCHEDULER_TERMINAL_RESULT_KEY) == {
        "run_id": "run",
        "output": "terminal",
    }


def test_scheduler_detail_exposes_run_and_successful_output_fields():
    detail = (
        PROJECT_ROOT
        / "webui/components/modals/scheduler/scheduler-task-detail.html"
    ).read_text(encoding="utf-8")
    store = (
        PROJECT_ROOT / "webui/components/modals/scheduler/scheduler-store.js"
    ).read_text(encoding="utf-8")
    sidebar = (
        PROJECT_ROOT / "webui/components/sidebar/tasks/tasks-list.html"
    ).read_text(encoding="utf-8")

    for label in (
        "Durable Task ID:",
        "Current Run ID:",
        "Last Run ID:",
        "Last Run Status:",
        "Last Successful Run:",
        "Last Successful Output:",
        "Output Handoff:",
    ):
        assert label in detail
    for field in (
        "current_run_id",
        "last_run_id",
        "last_run_status",
        "previous_run_output",
        "previous_run_output_sha256",
    ):
        assert field in store
    assert "selectTask(task.id)" in sidebar
    assert "reset(task.id)" in sidebar
    assert "openDetail(task.uuid)" in sidebar
    assert "deleteTask(task.uuid)" in sidebar
