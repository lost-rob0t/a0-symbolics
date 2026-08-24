from __future__ import annotations

from typing import Any

from helpers.tool import Response
from plugins._code_execution.tools.code_execution_tool import CodeExecution
from plugins._prolog_rlm.helpers.production_tools import git_arguments


class Git(CodeExecution):
    """Closed read-only Git adapter over Agent Zero's terminal runtime."""

    async def execute(
        self,
        action: str = "status",
        revision: str = "",
        path: str = "",
        query: str = "",
        staged: bool = False,
        limit: int = 20,
        session: int = 0,
        **kwargs: Any,
    ) -> Response:
        arguments, error = git_arguments(
            action or self.args.get("action"),
            revision=self.args.get("revision", revision),
            path=self.args.get("path", path),
            query=self.args.get("query", query),
            staged=self.args.get("staged", staged),
            limit=self.args.get("limit", limit),
            session=self.args.get("session", session),
        )
        if arguments is None:
            return Response(message=f"git rejected: {error}", break_loop=False)
        self.args = arguments
        return await super().execute(**arguments)
