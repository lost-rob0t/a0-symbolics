from helpers.extension import Extension
from helpers.task_scheduler import record_scheduler_terminal_response
from helpers.tool import Response


class RecordSchedulerTerminalResult(Extension):
    async def execute(
        self,
        response: Response | None = None,
        tool_name: str = "",
        **kwargs,
    ) -> None:
        if self.agent is None or response is None:
            return
        record_scheduler_terminal_response(self.agent, tool_name, response)
