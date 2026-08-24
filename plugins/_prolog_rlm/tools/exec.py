from __future__ import annotations

from typing import Any

from helpers.tool import Response
from plugins._code_execution.tools.code_execution_tool import CodeExecution
from plugins._prolog_rlm.helpers.production_tools import execution_arguments


class Exec(CodeExecution):
    """Canonical exec(lang, source_code) adapter over Agent Zero execution."""

    async def execute(
        self,
        lang: str = "",
        source_code: str = "",
        session: int = 0,
        reset: bool = False,
        allow_running: bool = False,
        **kwargs: Any,
    ) -> Response:
        arguments, error = execution_arguments(
            lang or self.args.get("lang"),
            source_code or self.args.get("source_code"),
            session=self.args.get("session", session),
            reset=self.args.get("reset", reset),
            allow_running=self.args.get("allow_running", allow_running),
        )
        if arguments is None:
            return Response(message=f"exec rejected: {error}", break_loop=False)
        self.args = arguments
        return await super().execute(**arguments)
