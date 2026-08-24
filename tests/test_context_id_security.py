from __future__ import annotations

from pathlib import Path

import pytest

from helpers import files, persist_chat


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
        "a" * 257,
    ],
)
def test_chat_paths_reject_untrusted_context_ids(ctxid: str) -> None:
    with pytest.raises(ValueError, match="context id"):
        persist_chat.get_chat_folder_path(ctxid)

    with pytest.raises(ValueError, match="context id"):
        persist_chat.get_chat_msg_files_folder(ctxid)


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
