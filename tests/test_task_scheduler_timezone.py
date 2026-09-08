import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers import task_scheduler
from helpers.task_scheduler import AdHocTask, ScheduledTask, TaskSchedule

class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 5, 9, 10, 0, tzinfo=timezone.utc)
        if tz is None:
            return value.replace(tzinfo=None)
        return value.astimezone(tz)


def test_scheduled_task_next_run_uses_schedule_timezone(monkeypatch):
    monkeypatch.setattr(task_scheduler, "datetime", FixedDateTime)
    task = ScheduledTask.create(
        name="rome morning",
        system_prompt="",
        prompt="remind me",
        schedule=TaskSchedule(
            minute="30",
            hour="9",
            day="10",
            month="5",
            weekday="*",
            timezone="Europe/Rome",
        ),
        timezone="Europe/Rome",
    )

    assert task.get_next_run() == datetime(2026, 5, 10, 7, 30, tzinfo=timezone.utc)


def test_scheduled_task_normalizes_legacy_local_timezone(monkeypatch):
    monkeypatch.setattr(task_scheduler, "datetime", FixedDateTime)
    monkeypatch.setattr(
        task_scheduler,
        "Localization",
        SimpleNamespace(get=lambda: SimpleNamespace(get_timezone=lambda: "Europe/Rome")),
    )
    task = ScheduledTask.create(
        name="legacy local",
        system_prompt="",
        prompt="remind me",
        schedule=TaskSchedule(
            minute="30",
            hour="9",
            day="10",
            month="5",
            weekday="*",
            timezone="local",
        ),
    )

    assert task.schedule.timezone == "Europe/Rome"
    assert task.get_next_run() == datetime(2026, 5, 10, 7, 30, tzinfo=timezone.utc)


def test_scheduler_missing_dedicated_context_logs_info(monkeypatch):
    calls = []

    class FakePrintStyle:
        @staticmethod
        def info(message):
            calls.append(("info", message))

        @staticmethod
        def warning(message):
            calls.append(("warning", message))

    class FakeAgentContext:
        @staticmethod
        def get(_context_id):
            return None

        def __init__(self, _config, id, name):
            self.id = id
            self.name = name

    monkeypatch.setattr(task_scheduler, "PrintStyle", FakePrintStyle)
    monkeypatch.setattr(task_scheduler, "AgentContext", FakeAgentContext)
    monkeypatch.setattr(task_scheduler, "initialize_agent", lambda: object())
    monkeypatch.setattr(task_scheduler, "save_tmp_chat", lambda _context: None)
    monkeypatch.setattr(
        task_scheduler.projects, "activate_project", lambda *_args, **_kwargs: None
    )

    task = AdHocTask.create(
        name="dedicated",
        system_prompt="",
        prompt="run this",
        token="123",
    )
    scheduler = object.__new__(task_scheduler.TaskScheduler)

    context = asyncio.run(scheduler._get_chat_context(task))

    assert context.id == task.context_id
    assert len(calls) == 1
    level, message = calls[0]
    assert level == "info"
    assert "creating dedicated context" in message


def test_scheduler_missing_shared_context_still_logs_warning(monkeypatch):
    calls = []

    class FakePrintStyle:
        @staticmethod
        def info(message):
            calls.append(("info", message))

        @staticmethod
        def warning(message):
            calls.append(("warning", message))

    class FakeAgentContext:
        @staticmethod
        def get(_context_id):
            return None

        def __init__(self, _config, id, name):
            self.id = id
            self.name = name

    monkeypatch.setattr(task_scheduler, "PrintStyle", FakePrintStyle)
    monkeypatch.setattr(task_scheduler, "AgentContext", FakeAgentContext)
    monkeypatch.setattr(task_scheduler, "initialize_agent", lambda: object())
    monkeypatch.setattr(task_scheduler, "save_tmp_chat", lambda _context: None)
    monkeypatch.setattr(
        task_scheduler.projects, "activate_project", lambda *_args, **_kwargs: None
    )

    task = AdHocTask.create(
        name="shared",
        system_prompt="",
        prompt="run this",
        token="123",
        context_id="shared-context",
    )
    scheduler = object.__new__(task_scheduler.TaskScheduler)

    context = asyncio.run(scheduler._get_chat_context(task))

    assert context.id == task.context_id
    assert len(calls) == 1
    level, message = calls[0]
    assert level == "warning"
    assert "context not found" in message


def test_scheduler_save_is_crash_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(
        task_scheduler,
        "get_abs_path",
        lambda *parts: str(tmp_path.joinpath(*parts)),
    )
    monkeypatch.setattr(task_scheduler, "datetime", FixedDateTime)

    task = ScheduledTask.create(
        name="crash safe",
        system_prompt="",
        prompt="persist me",
        schedule=TaskSchedule(
            minute="*",
            hour="*",
            day="*",
            month="*",
            weekday="*",
            timezone="UTC",
        ),
    )
    tasks = task_scheduler.SchedulerTaskList(tasks=[task])
    store = tmp_path / "usr" / "scheduler" / "tasks.json"

    asyncio.run(tasks.save())

    # The store must contain the saved task and no temp file may survive,
    # so a mid-write crash can never leave a truncated or missing store
    # that get() would silently recreate as empty.
    import json

    data = json.loads(store.read_text(encoding="utf-8"))
    assert [t["uuid"] for t in data["tasks"]] == [task.uuid]
    assert list(tmp_path.rglob("*.tmp")) == []

    task_scheduler.SchedulerTaskList._SchedulerTaskList__instance = None
    try:
        reloaded = asyncio.run(task_scheduler.SchedulerTaskList.get())
        assert [t.uuid for t in reloaded.tasks] == [task.uuid]
    finally:
        task_scheduler.SchedulerTaskList._SchedulerTaskList__instance = None
