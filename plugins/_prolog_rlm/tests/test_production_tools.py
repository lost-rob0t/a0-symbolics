from pathlib import Path

from helpers.responses_tools import _schema_from_prompt


ROOT = Path(__file__).resolve().parents[3]


def test_code_execution_publishes_a_nonempty_native_schema():
    prompt = (
        ROOT
        / "plugins"
        / "_code_execution"
        / "prompts"
        / "agent.system.tool.code_exe.md"
    ).read_text(encoding="utf-8")
    schema = _schema_from_prompt(prompt)

    assert schema["type"] == "object"
    assert schema["required"] == ["runtime"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "runtime",
        "code",
        "session",
        "reset",
        "allow_running",
    }


def test_prolog_rlm_has_one_agent_facing_tool():
    tools = sorted(
        path.stem
        for path in (ROOT / "plugins" / "_prolog_rlm" / "tools").glob("*.py")
        if path.name != "__init__.py"
    )

    assert tools == ["prolog_rlm"]
