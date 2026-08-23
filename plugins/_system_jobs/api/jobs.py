from __future__ import annotations

from helpers.api import ApiHandler, Request, Response

from plugins._system_jobs.helpers import jobs as jobs_helper


class Jobs(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = str(input.get("action", "list") or "list").strip().lower()
        try:
            if action == "list":
                return {
                    "ok": True,
                    "jobs": jobs_helper.list_jobs(),
                    "status": jobs_helper.status(),
                }
            if action in {"save", "create", "update"}:
                job = jobs_helper.save_job(
                    job_id=str(input.get("id", "") or ""),
                    name=str(input.get("name", "") or ""),
                    schedule=str(input.get("schedule", "") or ""),
                    script=str(input.get("script", "") or ""),
                    workdir=str(input.get("workdir", "/a0/usr/workdir") or "/a0/usr/workdir"),
                    enabled=bool(input.get("enabled", True)),
                )
                return {"ok": True, "job": job}
            if action == "delete":
                jobs_helper.delete_job(str(input.get("id", "") or ""))
                return {"ok": True}
            if action == "run":
                result = jobs_helper.run_job(str(input.get("id", "") or ""))
                return {"ok": True, "run": result}
            if action == "log":
                return {
                    "ok": True,
                    "log": jobs_helper.read_log(
                        str(input.get("id", "") or ""),
                        int(input.get("max_bytes", 200_000) or 200_000),
                    ),
                }
            if action == "sync":
                jobs_helper.sync_crontab()
                return {"ok": True, "status": jobs_helper.status()}
        except FileNotFoundError as error:
            return Response(status=404, response=str(error))
        except (ValueError, RuntimeError) as error:
            return Response(status=400, response=str(error))

        return Response(status=400, response=f"Unknown action: {action}")
