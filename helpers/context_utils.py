"""Shared context helper used by both ApiHandler and WsHandler."""

import re
import threading
from typing import Union

ThreadLockType = Union[threading.Lock, threading.RLock]

_CONTEXT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def validate_context_id(ctxid: str) -> str:
    """Validate an externally meaningful Agent Zero context identifier.

    Context IDs are opaque identifiers, never filesystem paths. Generated IDs
    are ASCII alphanumeric; hyphens/underscores remain accepted for compatible
    imported identifiers.
    """

    if not isinstance(ctxid, str) or not _CONTEXT_ID_RE.fullmatch(ctxid):
        raise ValueError(
            "context id must be 1-128 ASCII letters, digits, '_' or '-'"
        )
    return ctxid


def use_context(lock: ThreadLockType, ctxid: str, create_if_not_exists: bool = True):
    from agent import AgentContext
    from helpers import projects
    from initialize import initialize_agent

    with lock:
        if not ctxid:
            first = AgentContext.first()
            if first:
                AgentContext.use(first.id)
                return first
            context = AgentContext(config=initialize_agent(), set_current=True)
            projects.reconcile_agent_profile(
                context, projects.get_context_project_name(context)
            )
            return context

        ctxid = validate_context_id(ctxid)
        got = AgentContext.use(ctxid)
        if got:
            return got
        if create_if_not_exists:
            context = AgentContext(
                config=initialize_agent(), id=ctxid, set_current=True
            )
            projects.reconcile_agent_profile(
                context, projects.get_context_project_name(context)
            )
            return context
        raise Exception(f"Context {ctxid} not found")
