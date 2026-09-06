from helpers.api import ApiHandler, Input, Output, Request
from helpers.task_scheduler import TaskScheduler, TaskState
from helpers.localization import Localization
from agent import AgentContext
from helpers import persist_chat


class SchedulerTaskDelete(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        """
        Delete a task from the scheduler by ID
        """
        # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
        if timezone := input.get("timezone", None):
            Localization.get().set_timezone(timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Get task ID from input
        task_id: str = input.get("task_id", "")

        if not task_id:
            return {"error": "Missing required field: task_id"}

        # Check if the task exists first
        task = scheduler.get_task_by_uuid(task_id)
        if not task:
            return {"error": f"Task with ID {task_id} not found"}

        context = AgentContext.get(task.current_run_id) if task.current_run_id else None

        # Cancel the fresh per-occurrence run before removing durable task state.
        if task.state == TaskState.RUNNING:
            scheduler.cancel_running_task(task_id, terminate_thread=True)
            if context:
                context.reset()

        legacy_context = AgentContext.get(task.context_id) if task.context_id else None
        if legacy_context and legacy_context.id == task.uuid:
            AgentContext.remove(legacy_context.id)
            persist_chat.remove_chat(legacy_context.id)

        # Remove the task
        await scheduler.remove_task_by_uuid(task_id)

        return {"success": True, "message": f"Task {task_id} deleted successfully"}
