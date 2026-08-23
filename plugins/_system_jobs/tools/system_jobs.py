from __future__ import annotations

import json

from helpers.tool import Response, Tool
from plugins._system_jobs.helpers import jobs as jobs_helper


class SystemJobsTool(Tool):
    async def execute(
        self,
        action: str = "list",
        id: str = "",
        name: str = "",
        schedule: str = "",
        script: str = "",
        workdir: str = "/a0/usr/workdir",
        enabled: bool = True,
        **kwargs,
    ) -> Response:
        action = str(action or "list").strip().lower()
        try:
            if action in {"list", "status"}:
                payload = {
                    "status": jobs_helper.status(),
                    "jobs": jobs_helper.list_jobs(),
                }
                return Response(message=json.dumps(payload, indent=2), break_loop=False)
            if action in {"create", "save", "update"}:
                job = jobs_helper.save_job(
                    job_id=id,
                    name=name,
                    schedule=schedule,
                    script=script,
                    workdir=workdir,
                    enabled=enabled,
                )
                return Response(message=json.dumps(job, indent=2), break_loop=False)
            if action == "delete":
                jobs_helper.delete_job(id)
                return Response(message=f"Deleted system job {id}.", break_loop=False)
            if action == "run":
                result = jobs_helper.run_job(id)
                return Response(message=json.dumps(result, indent=2), break_loop=False)
            if action == "log":
                return Response(message=jobs_helper.read_log(id), break_loop=False)
            if action == "sync":
                jobs_helper.sync_crontab()
                return Response(message="System Jobs crontab synchronized.", break_loop=False)
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            return Response(message=str(error), break_loop=False)

        return Response(
            message="Unknown action. Supported actions: list, status, create, update, delete, run, log, sync.",
            break_loop=False,
        )
