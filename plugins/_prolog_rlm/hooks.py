from plugins._prolog_context_compiler.helpers.catalog import register_permanent_tools


PERMANENT_TOOLS = ("exec", "git", "patch", "prolog_rlm")


def register_context_tools() -> None:
    """Declare core visibility without granting execution authority."""

    register_permanent_tools(*PERMANENT_TOOLS)
