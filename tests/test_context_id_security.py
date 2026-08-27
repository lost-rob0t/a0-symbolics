from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from api.chat_create import CreateChat
from api.chat_remove import RemoveChat
from helpers import files, persist_chat
from helpers.context_utils import validate_context_id


@pytest.mark.parametrize(
    "ctxid",
    [
        "Abc123",
        "chat_01",
        "550e8400-e29b-41d4-a716-446655440000",
    ],
)
def test_valid_context_ids_remain_compatible(ctxid: str) -> None:
    assert validate_context_id(ctxid) == ctxid
    assert Path(persist_chat.get_chat_folder_path(ctxid)).name == ctxid


@pytest.mark.parametrize(
    "ctxid",
    [
        "..",
        "../escape",
        "../../escape",
        "nested/chat",
        r"nested\\chat",
        "/absolute",
        "file://escape",
        "",
        "   ",
        "nul\x00id",
        "line\nbreak",
        "é",
        "a" * 129,
    ],
)
def test_chat_paths_reject_untrusted_context_ids(ctxid: str) -> None:
    with pytest.raises(ValueError, match="context id"):
        persist_chat.get_chat_folder_path(ctxid)

    with pytest.raises(ValueError, match="context id"):
        persist_chat.get_chat_msg_files_folder(ctxid)


def test_chat_create_rejects_invalid_requested_id_before_side_effects(monkeypatch) -> None:
    handler = CreateChat(None, threading.RLock())
    monkeypatch.setattr(
        handler,
        "use_context",
        lambda *_args, **_kwargs: pytest.fail("invalid ID reached context creation"),
    )

    response = asyncio.run(handler.process({"new_context": "../escape"}, None))

    assert response.status_code == 400


def test_chat_remove_rejects_invalid_id_before_side_effects(monkeypatch) -> None:
    from helpers.task_scheduler import TaskScheduler

    handler = RemoveChat(None, threading.RLock())
    monkeypatch.setattr(
        TaskScheduler,
        "get",
        lambda: pytest.fail("invalid ID reached destructive scheduler path"),
    )

    response = asyncio.run(handler.process({"context": "../escape"}, None))

    assert response.status_code == 400


def test_remove_chat_cannot_escape_chat_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(files, "_base_dir", str(tmp_path))
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    marker = sentinel / "keep.txt"
    marker.write_text("must survive", encoding="utf-8")

    with pytest.raises(ValueError, match="context id"):
        persist_chat.remove_chat("../../sentinel")

    assert sentinel.is_dir()
    assert marker.read_text(encoding="utf-8") == "must survive"


def test_remove_message_files_cannot_escape_chat_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(files, "_base_dir", str(tmp_path))
    sentinel = tmp_path / "sentinel" / "messages"
    sentinel.mkdir(parents=True)
    marker = sentinel / "keep.txt"
    marker.write_text("must survive", encoding="utf-8")

    with pytest.raises(ValueError, match="context id"):
        persist_chat.remove_msg_files("../../sentinel")

    assert sentinel.is_dir()
    assert marker.read_text(encoding="utf-8") == "must survive"


@pytest.mark.parametrize("target_kind", ["outside", "chat-root", "other-chat"])
def test_symlinked_chat_id_is_never_a_storage_alias(
    monkeypatch, tmp_path: Path, target_kind: str
) -> None:
    monkeypatch.setattr(files, "_base_dir", str(tmp_path))
    chats = tmp_path / "usr" / "chats"
    chats.mkdir(parents=True)

    if target_kind == "outside":
        target = tmp_path / "outside"
        target.mkdir()
    elif target_kind == "chat-root":
        target = chats
    else:
        target = chats / "otherchat"
        target.mkdir()

    (chats / "safeid").symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="aliases another chat storage location"):
        persist_chat.get_chat_folder_path("safeid")


def test_message_directory_symlink_cannot_escape_chat(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(files, "_base_dir", str(tmp_path))
    chat = tmp_path / "usr" / "chats" / "safeid"
    outside = tmp_path / "outside"
    chat.mkdir(parents=True)
    outside.mkdir()
    (chat / "messages").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="outside chat storage"):
        persist_chat.get_chat_msg_files_folder("safeid")


def test_load_rejects_persisted_id_that_does_not_match_chat_folder(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(persist_chat, "_convert_v080_chats", lambda: None)
    monkeypatch.setattr(
        persist_chat.files,
        "list_files",
        lambda folder, pattern="*": ["safeid"],
    )
    monkeypatch.setattr(
        persist_chat.files,
        "exists",
        lambda path: True,
    )
    monkeypatch.setattr(
        persist_chat.files,
        "read_file",
        lambda path: '{"id": "otherid"}',
    )
    monkeypatch.setattr(
        persist_chat,
        "_deserialize_context",
        lambda data: pytest.fail("mismatched context reached deserialization"),
    )

    assert persist_chat.load_tmp_chats() == []
    assert "does not match chat folder" in capsys.readouterr().out
