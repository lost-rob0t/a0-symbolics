from __future__ import annotations

import re
import shlex
from typing import Any


_LANGUAGES = {
    "bash": "terminal",
    "javascript": "nodejs",
    "js": "nodejs",
    "node": "nodejs",
    "nodejs": "nodejs",
    "py": "python",
    "python": "python",
    "sh": "terminal",
    "shell": "terminal",
    "terminal": "terminal",
}
_REVISION = re.compile(r"[A-Za-z0-9._/@{}~^:+-]+")


def execution_arguments(
    lang: Any,
    source_code: Any,
    *,
    session: Any = 0,
    reset: Any = False,
    allow_running: Any = False,
) -> tuple[dict[str, Any] | None, str]:
    language = str(lang or "").strip().lower()
    runtime = _LANGUAGES.get(language)
    if runtime is None:
        return None, (
            "unsupported language; use shell, python, or javascript "
            "(terminal, bash, sh, py, js, node, and nodejs are aliases)"
        )
    code = str(source_code or "")
    if not code.strip():
        return None, "source_code is required"
    try:
        session_id = int(session)
    except (TypeError, ValueError):
        return None, "session must be an integer"
    if session_id < 0:
        return None, "session must be non-negative"
    return {
        "runtime": runtime,
        "code": code,
        "session": session_id,
        "reset": _flag(reset),
        "allow_running": _flag(allow_running),
    }, ""


def git_arguments(
    action: Any,
    *,
    revision: Any = "",
    path: Any = "",
    query: Any = "",
    staged: Any = False,
    limit: Any = 20,
    session: Any = 0,
) -> tuple[dict[str, Any] | None, str]:
    operation = str(action or "status").strip().lower()
    revision_text = str(revision or "").strip()
    path_text = str(path or "").strip()
    query_text = str(query or "")

    if revision_text and not _valid_revision(revision_text):
        return None, "revision contains unsupported characters or begins with '-'"
    if "\x00" in path_text or "\x00" in query_text:
        return None, "path and query must not contain NUL bytes"
    try:
        session_id = int(session)
        count = int(limit)
    except (TypeError, ValueError):
        return None, "session and limit must be integers"
    if session_id < 0:
        return None, "session must be non-negative"
    count = max(1, min(count, 200))

    command: list[str] = ["git", "--no-pager"]
    if operation == "status":
        command.extend(["status", "--short", "--branch"])
    elif operation == "branch":
        command.extend(["branch", "--show-current"])
    elif operation == "diff":
        command.extend(["diff", "--no-ext-diff", "--no-color"])
        if _flag(staged):
            command.append("--cached")
        if revision_text:
            command.append(revision_text)
        _append_path(command, path_text)
    elif operation == "show":
        command.extend(
            ["show", "--no-ext-diff", "--no-color", revision_text or "HEAD"]
        )
        _append_path(command, path_text)
    elif operation == "log":
        command.extend(
            [
                "log",
                "--no-color",
                f"--max-count={count}",
                "--date=iso-strict",
                "--pretty=format:%h %ad %an %s",
            ]
        )
        if revision_text:
            command.append(revision_text)
        _append_path(command, path_text)
    elif operation == "grep":
        if not query_text:
            return None, "query is required for git grep"
        command.extend(["grep", "-n", "--full-name", "-e", query_text])
        _append_path(command, path_text)
    else:
        return None, "unsupported git action; use status, branch, diff, show, log, or grep"

    return {
        "runtime": "terminal",
        "code": shlex.join(command),
        "session": session_id,
        "reset": False,
        "allow_running": False,
    }, ""


def _valid_revision(value: str) -> bool:
    return not value.startswith("-") and _REVISION.fullmatch(value) is not None


def _append_path(command: list[str], path: str) -> None:
    if path:
        command.extend(["--", path])


def _flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
