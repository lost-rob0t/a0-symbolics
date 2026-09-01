from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import HumanMessage, SystemMessage

from helpers.skills import Skill
from plugins._prolog_rlm.helpers.model_turn import build_turn_request


class FakeAgent:
    def __init__(self) -> None:
        self.loop_data = SimpleNamespace(user_message=None)
        self.data = {}

    def get_data(self, name):
        return self.data.get(name)

    def set_data(self, name, value):
        self.data[name] = value


def test_agent_zero_skills_are_projected_as_typed_prolog_rlm_skill_units():
    agent = FakeAgent()
    skill = Skill(
        name="repo-review",
        description="Review a repository before changing it",
        path=Path("/a0/usr/skills/repo-review"),
        skill_md_path=Path("/a0/usr/skills/repo-review/SKILL.md"),
        tags=["git", "review"],
        triggers=["review repository"],
        allowed_tools=["code_execution_tool"],
        metadata={"suggests": ["test-changes"]},
        raw_frontmatter={"requires": ["inspect-repo"]},
        content="Read the repository rules, inspect current state, then review changes.",
    )

    with (
        patch(
            "plugins._prolog_rlm.helpers.model_turn.skills.list_skills",
            return_value=[skill],
        ),
        patch(
            "plugins._prolog_rlm.helpers.model_turn.build_responses_function_tools",
            return_value=([], {}),
        ),
        patch(
            "plugins._prolog_rlm.helpers.model_turn.get_chat_model_config",
            return_value={
                "provider": "openrouter",
                "name": "openai/gpt-test",
                "ctx_length": 200_000,
            },
        ),
    ):
        request = build_turn_request(
            agent,
            [SystemMessage(content="System contract"), HumanMessage(content="review it")],
        )

    units = request["compile_request"]["units"]
    projected = next(unit for unit in units if unit.get("name") == "repo-review")
    assert projected["format"] == "agent_zero_skill"
    assert projected["kind"] == "skill"
    assert projected["content"].startswith("Read the repository rules")
    assert projected["aliases"] == ["review repository"]
    assert projected["requires"] == ["inspect-repo"]
    assert projected["suggests"] == ["test-changes"]
    assert projected["tags"] == ["git", "review"]
    assert projected["allowed_tools"] == ["code_execution_tool"]
    assert projected["permanent"] is False


def test_skill_catalog_is_scoped_through_agent_zero_discovery():
    agent = FakeAgent()
    with (
        patch(
            "plugins._prolog_rlm.helpers.model_turn.skills.list_skills",
            return_value=[],
        ) as list_skills,
        patch(
            "plugins._prolog_rlm.helpers.model_turn.build_responses_function_tools",
            return_value=([], {}),
        ),
        patch(
            "plugins._prolog_rlm.helpers.model_turn.get_chat_model_config",
            return_value={
                "provider": "openrouter",
                "name": "openai/gpt-test",
                "ctx_length": 200_000,
            },
        ),
    ):
        build_turn_request(
            agent,
            [SystemMessage(content="System contract"), HumanMessage(content="hello")],
        )

    list_skills.assert_called_once_with(agent=agent, include_content=True)
