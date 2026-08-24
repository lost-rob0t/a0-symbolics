from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers.responses_tools import _schema_from_prompt
from plugins._prolog_context_compiler.helpers.catalog import (
    permanent_tools,
    register_permanent_tools,
)
from plugins._prolog_rlm.helpers.production_tools import (
    execution_arguments,
    git_arguments,
)


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def test_exec_maps_public_language_api_to_canonical_runtimes():
    shell, error = execution_arguments(
        "shell", "printf ok", session="2", reset="false"
    )
    python, _ = execution_arguments("py", "print('ok')")
    node, _ = execution_arguments("javascript", "console.log('ok')")

    assert error == ""
    assert shell == {
        "runtime": "terminal",
        "code": "printf ok",
        "session": 2,
        "reset": False,
        "allow_running": False,
    }
    assert python["runtime"] == "python"
    assert node["runtime"] == "nodejs"
    assert execution_arguments("prolog", "halt")[0] is None
    assert execution_arguments("shell", "  ")[0] is None


def test_git_pack_is_closed_read_only_and_shell_quotes_model_data():
    diff, error = git_arguments(
        "diff", revision="HEAD~2..HEAD", path="dir/file name.py", staged=True
    )
    grep, _ = git_arguments("grep", query="$(touch /tmp/nope)", path="src")

    assert error == ""
    assert diff["runtime"] == "terminal"
    assert diff["code"] == (
        "git --no-pager diff --no-ext-diff --no-color --cached "
        "'HEAD~2..HEAD' -- 'dir/file name.py'"
    )
    assert "'$(touch /tmp/nope)'" in grep["code"]
    assert git_arguments("commit")[0] is None
    assert git_arguments("show", revision="--exec=bad")[0] is None


def test_production_prompts_publish_strict_native_schemas():
    for name in ("exec", "git", "patch"):
        prompt = (PLUGIN_ROOT / "prompts" / f"agent.system.tool.{name}.md").read_text()
        schema = _schema_from_prompt(prompt)
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert schema["properties"]


def test_plugin_tools_reuse_canonical_implementations():
    exec_module = _load_tool("exec")
    git_module = _load_tool("git")
    patch_module = _load_tool("patch")

    from plugins._code_execution.tools.code_execution_tool import CodeExecution
    from plugins._text_editor.tools.text_editor import TextEditor

    assert issubclass(exec_module.Exec, CodeExecution)
    assert issubclass(git_module.Git, CodeExecution)
    assert issubclass(patch_module.Patch, TextEditor)


@pytest.mark.asyncio
async def test_exec_and_git_adapters_delegate_normalized_args_to_code_execution(
    monkeypatch,
):
    exec_module = _load_tool("exec")
    git_module = _load_tool("git")

    from helpers.tool import Response
    from plugins._code_execution.tools.code_execution_tool import CodeExecution

    seen = []

    async def capture(self, **kwargs):
        seen.append(dict(self.args))
        return Response(message="delegated", break_loop=False)

    monkeypatch.setattr(CodeExecution, "execute", capture)
    agent = SimpleNamespace()
    exec_tool = exec_module.Exec(
        agent, "exec", None, {"lang": "py", "source_code": "print(1)"}, "", None
    )
    git_tool = git_module.Git(
        agent, "git", None, {"action": "status"}, "", None
    )

    assert (await exec_tool.execute()).message == "delegated"
    assert (await git_tool.execute()).message == "delegated"
    assert seen[0]["runtime"] == "python"
    assert seen[0]["code"] == "print(1)"
    assert seen[1]["code"] == "git --no-pager status --short --branch"


@pytest.mark.asyncio
async def test_patch_adapter_delegates_to_canonical_patch_action(monkeypatch):
    patch_module = _load_tool("patch")

    from helpers.tool import Response
    from plugins._text_editor.tools.text_editor import TextEditor

    seen = {}

    async def capture(self, **kwargs):
        seen.update(kwargs)
        return Response(message="patched", break_loop=False)

    monkeypatch.setattr(TextEditor, "execute", capture)
    tool = patch_module.Patch(
        SimpleNamespace(),
        "patch",
        None,
        {"path": "file.py", "old_text": "old", "new_text": "new"},
        "",
        None,
    )

    assert (await tool.execute()).message == "patched"
    assert seen["action"] == "patch"
    assert seen["path"] == "file.py"
    assert seen["old_text"] == "old"
    assert seen["new_text"] == "new"


def test_permanent_tool_registration_api_keeps_production_core_visible():
    assert {"exec", "git", "patch", "prolog_rlm"} <= permanent_tools({})

    register_permanent_tools("external_pack_tool")
    assert "external_pack_tool" in permanent_tools({})


def _load_tool(name: str):
    path = PLUGIN_ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"a0_prolog_tool_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
