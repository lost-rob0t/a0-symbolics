from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("A0_SYSTEM_JOBS_DIR", "/a0/usr/system-jobs"))
JOBS_FILE = ROOT / "jobs.json"
SCRIPTS_DIR = ROOT / "scripts"
LOGS_DIR = ROOT / "logs"
BEGIN_MARKER = "# BEGIN A0 SYSTEM JOBS"
END_MARKER = "# END A0 SYSTEM JOBS"
PATH_VALUE = "/root/.nix-profile/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
VALID_MACROS = {
    "@reboot",
    "@yearly",
    "@annually",
    "@monthly",
    "@weekly",
    "@daily",
    "@midnight",
    "@hourly",
}
FIELD_RE = re.compile(r"^[A-Za-z0-9*/,-]+$")
ID_RE = re.compile(r"^[a-f0-9]{32}$")
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def _validate_schedule(schedule: str) -> str:
    schedule = str(schedule or "").strip()
    if schedule in VALID_MACROS:
        return schedule
    fields = schedule.split()
    if len(fields) != 5 or any(not FIELD_RE.fullmatch(field) for field in fields):
        raise ValueError("Schedule must be a five-field cron expression or a standard @daily/@hourly-style macro")
    return " ".join(fields)


def _validate_workdir(workdir: str) -> str:
    workdir = str(workdir or "/a0/usr/workdir").strip()
    path = Path(workdir)
    if not path.is_absolute():
        raise ValueError("Working directory must be an absolute path")
    if "\x00" in workdir:
        raise ValueError("Working directory contains an invalid NUL byte")
    return workdir


def _validate_id(job_id: str) -> str:
    job_id = str(job_id or "").strip().lower()
    if not ID_RE.fullmatch(job_id):
        raise ValueError("Invalid system job id")
    return job_id


def _load_jobs_unlocked() -> list[dict[str, Any]]:
    _ensure_dirs()
    if not JOBS_FILE.exists():
        return []
    try:
        raw = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {JOBS_FILE}: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError(f"{JOBS_FILE} must contain a JSON list")
    jobs = [job for job in raw if isinstance(job, dict)]
    return sorted(jobs, key=lambda item: str(item.get("name", "")).lower())


def list_jobs() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(job) for job in _load_jobs_unlocked()]


def _write_jobs_unlocked(jobs: list[dict[str, Any]]) -> None:
    _atomic_write(JOBS_FILE, json.dumps(jobs, indent=2, sort_keys=True) + "\n")


def _script_path(job_id: str) -> Path:
    return SCRIPTS_DIR / f"{job_id}.sh"


def _log_path(job_id: str) -> Path:
    return LOGS_DIR / f"{job_id}.log"


def _render_script(workdir: str, script: str) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"cd -- {shlex.quote(workdir)}\n\n"
        f"{script.rstrip()}\n"
    )


def _crontab_binary() -> str:
    binary = shutil.which("crontab") or "/root/.nix-profile/bin/crontab"
    if not Path(binary).is_file():
        raise RuntimeError("crontab is unavailable; apply the a0-symbolics Home Manager profile first")
    return binary


def _strip_managed_block(text: str) -> str:
    pattern = re.compile(
        rf"(?ms)^{re.escape(BEGIN_MARKER)}\n.*?^{re.escape(END_MARKER)}\n?"
    )
    return pattern.sub("", text).strip()


def _sync_crontab_unlocked(jobs: list[dict[str, Any]]) -> None:
    binary = _crontab_binary()
    current = subprocess.run(
        [binary, "-l"],
        check=False,
        text=True,
        capture_output=True,
        timeout=10,
    )
    unmanaged = _strip_managed_block(current.stdout if current.returncode == 0 else "")

    block = [
        BEGIN_MARKER,
        "SHELL=/bin/bash",
        f"PATH={PATH_VALUE}",
        "HOME=/root",
        'MAILTO=""',
    ]
    for job in jobs:
        if not bool(job.get("enabled", True)):
            continue
        job_id = _validate_id(str(job.get("id", "")))
        schedule = _validate_schedule(str(job.get("schedule", "")))
        name = str(job.get("name", "system job")).replace("\n", " ")[:120]
        script_path = _script_path(job_id)
        log_path = _log_path(job_id)
        block.append(f"# {job_id} {name}")
        block.append(
            f"{schedule} /bin/bash {shlex.quote(str(script_path))} >> {shlex.quote(str(log_path))} 2>&1"
        )
    block.append(END_MARKER)

    merged = ""
    if unmanaged:
        merged += unmanaged.rstrip() + "\n\n"
    merged += "\n".join(block) + "\n"

    result = subprocess.run(
        [binary, "-"],
        input=merged,
        check=False,
        text=True,
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "crontab update failed").strip())


def sync_crontab() -> None:
    with _LOCK:
        _sync_crontab_unlocked(_load_jobs_unlocked())


def save_job(
    *,
    job_id: str = "",
    name: str,
    schedule: str,
    script: str,
    workdir: str = "/a0/usr/workdir",
    enabled: bool = True,
) -> dict[str, Any]:
    name = str(name or "").strip()
    if not name:
        raise ValueError("Job name is required")
    if len(name) > 120:
        raise ValueError("Job name must be 120 characters or fewer")
    schedule = _validate_schedule(schedule)
    workdir = _validate_workdir(workdir)
    script = str(script or "")
    if not script.strip():
        raise ValueError("Script body is required")
    if len(script.encode("utf-8")) > 256 * 1024:
        raise ValueError("Script body must be 256 KiB or smaller")

    with _LOCK:
        jobs = _load_jobs_unlocked()
        existing = None
        if job_id:
            job_id = _validate_id(job_id)
            existing = next((job for job in jobs if job.get("id") == job_id), None)
            if existing is None:
                raise FileNotFoundError("System job not found")
        else:
            job_id = uuid.uuid4().hex

        now = _now()
        job = {
            "id": job_id,
            "name": name,
            "schedule": schedule,
            "script": script,
            "workdir": workdir,
            "enabled": bool(enabled),
            "created_at": existing.get("created_at", now) if existing else now,
            "updated_at": now,
            "script_path": str(_script_path(job_id)),
            "log_path": str(_log_path(job_id)),
        }

        _atomic_write(_script_path(job_id), _render_script(workdir, script), mode=0o700)
        jobs = [candidate for candidate in jobs if candidate.get("id") != job_id]
        jobs.append(job)
        jobs.sort(key=lambda item: str(item.get("name", "")).lower())
        _write_jobs_unlocked(jobs)
        _sync_crontab_unlocked(jobs)
        return dict(job)


def delete_job(job_id: str) -> None:
    job_id = _validate_id(job_id)
    with _LOCK:
        jobs = _load_jobs_unlocked()
        if not any(job.get("id") == job_id for job in jobs):
            raise FileNotFoundError("System job not found")
        jobs = [job for job in jobs if job.get("id") != job_id]
        _write_jobs_unlocked(jobs)
        _sync_crontab_unlocked(jobs)
        _script_path(job_id).unlink(missing_ok=True)
        _log_path(job_id).unlink(missing_ok=True)


def run_job(job_id: str) -> dict[str, Any]:
    job_id = _validate_id(job_id)
    with _LOCK:
        job = next((item for item in _load_jobs_unlocked() if item.get("id") == job_id), None)
        if job is None:
            raise FileNotFoundError("System job not found")
        script_path = _script_path(job_id)
        if not script_path.exists():
            _atomic_write(
                script_path,
                _render_script(str(job.get("workdir", "/a0/usr/workdir")), str(job.get("script", ""))),
                mode=0o700,
            )
        log_path = _log_path(job_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PATH"] = PATH_VALUE
        log = log_path.open("ab", buffering=0)
        try:
            process = subprocess.Popen(
                ["/bin/bash", str(script_path)],
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
        finally:
            log.close()
        return {"id": job_id, "pid": process.pid, "log_path": str(log_path)}


def read_log(job_id: str, max_bytes: int = 200_000) -> str:
    job_id = _validate_id(job_id)
    path = _log_path(job_id)
    if not path.exists():
        return ""
    max_bytes = max(1, min(int(max_bytes), 1_000_000))
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes), os.SEEK_SET)
        return handle.read().decode("utf-8", errors="replace")


def status() -> dict[str, Any]:
    cron = shutil.which("cron") or ""
    crontab = shutil.which("crontab") or ""
    running = False
    pgrep = shutil.which("pgrep")
    if pgrep:
        running = subprocess.run(
            [pgrep, "-x", "cron"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    return {
        "cron": cron,
        "crontab": crontab,
        "running": running,
        "root": str(ROOT),
        "jobs_file": str(JOBS_FILE),
    }
