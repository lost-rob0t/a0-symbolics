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


def _skill(name: str, path: str) -> Skill:
    return Skill(
        name=name,
        description=f"{name} skill",
        path=Path(path),
        skill_md_path=Path(path) / "SKILL.md",
    )


def test_agent_zero_skills_are_projected_as_exact_admitted_packages():
    agent = FakeAgent()
    visible = [
        _skill("repo-review", "/a0/usr/skills/repo-review"),
        _skill("test-changes", "/a0/plugins/review/skills/test-changes"),
    ]

    with (
        patch(
            "plugins._prolog_rlm.helpers.model_turn.skills.list_skills",
            return_value=visible,
        ),
        patch(
            "plugins._prolog_rlm.helpers.model_turn.skills.get_loaded_skill_names",
            return_value=["repo-review", "hidden-skill"],
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
            {"include_core_skills": True},
        )

    compile_request = request["compile_request"]
    assert compile_request["skill_packages"] == [
        {"name": "repo-review", "path": "/a0/usr/skills/repo-review"},
        {
            "name": "test-changes",
            "path": "/a0/plugins/review/skills/test-changes",
        },
    ]
    # Loaded skills are only pinned if they survived Agent Zero's current
    # visibility/precedence policy. Hidden/stale names never cross the ABI.
    assert compile_request["selected_skills"] == ["repo-review"]
    assert compile_request["include_core_skills"] is True
    assert not any(
        unit.get("format") == "agent_zero_skill"
        for unit in compile_request["units"]
    )


def test_skill_catalog_uses_agent_zero_scope_and_does_not_read_bodies_in_python():
    agent = FakeAgent()
    with (
        patch(
            "plugins._prolog_rlm.helpers.model_turn.skills.list_skills",
            return_value=[],
        ) as list_skills,
        patch(
            "plugins._prolog_rlm.helpers.model_turn.skills.get_loaded_skill_names",
            return_value=[],
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
        build_turn_request(
            agent,
            [SystemMessage(content="System contract"), HumanMessage(content="hello")],
        )

    list_skills.assert_called_once_with(
        agent=agent,
        include_content=False,
        include_hidden=False,
    )
