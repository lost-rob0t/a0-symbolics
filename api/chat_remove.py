from helpers.api import ApiHandler, Input, Output, Request, Response
from agent import AgentContext
from helpers import persist_chat
from helpers.context_utils import validate_context_id
from helpers.task_scheduler import TaskScheduler


class RemoveChat(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        try:
            ctxid = validate_context_id(input.get("context", ""))
        except ValueError as error:
            return Response(str(error), status=400, mimetype="text/plain")

        scheduler = TaskScheduler.get()
        scheduler.cancel_tasks_by_context(ctxid, terminate_thread=True)

        context = AgentContext.use(ctxid)
        if context:
            # stop processing any tasks
            context.reset()

        AgentContext.remove(ctxid)
        persist_chat.remove_chat(ctxid)

        await scheduler.reload()

        tasks = scheduler.get_tasks_by_context_id(ctxid)
        for task in tasks:
            await scheduler.remove_task_by_uuid(task.uuid)

        # Context removal affects global chat/task lists in all tabs.
        from helpers.state_monitor_integration import mark_dirty_all
        mark_dirty_all(reason="api.chat_remove.RemoveChat")

        return {
            "message": "Context removed.",
        }
