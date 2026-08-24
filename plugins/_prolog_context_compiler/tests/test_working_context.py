from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from plugins._prolog_context_compiler.helpers.working_context import (
    build_working_context_request,
    projected_messages,
    provider_payload_tokens,
)


def test_working_context_keeps_recent_correction_and_adapts_dox():
    messages = [
        SystemMessage(content="core"),
        HumanMessage(content="# project instructions\nUse the current checkout."),
        AIMessage(content="old claim: use branch stale"),
        HumanMessage(content="irrelevant " * 5000),
        HumanMessage(content="Correction: use branch current"),
        AIMessage(content="Acknowledged"),
    ]
    request, recent, system = build_working_context_request(
        messages,
        "continue with branch current",
        {"recent_message_count": 2, "max_working_unit_chars": 2000},
    )

    assert system is messages[0]
    assert [message.content for message in recent] == [
        "Correction: use branch current",
        "Acknowledged",
    ]
    assert request["units"][0]["format"] == "dox"
    assert request["units"][0]["permanent"] is True
    assert len(request["units"][2]["content"]) <= 2020


def test_projection_replaces_unbounded_old_history_with_bounded_result():
    recent = [HumanMessage(content="latest correction")]
    messages = projected_messages(
        SystemMessage(content="core"), "selected evidence", recent
    )

    assert len(messages) == 3
    assert "selected evidence" in messages[1].content
    assert messages[-1].content == "latest correction"
    assert provider_payload_tokens(messages, []) < 100
