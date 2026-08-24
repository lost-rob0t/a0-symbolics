from __future__ import annotations

from typing import Any

from helpers.tool import Response
from plugins._text_editor.tools.text_editor import TextEditor


class Patch(TextEditor):
    """Patch-only adapter preserving the canonical text editor safeguards."""

    async def execute(
        self,
        path: str = "",
        edits: Any = None,
        patch_text: str | None = None,
        old_text: str | None = None,
        new_text: str | None = None,
        **kwargs: Any,
    ) -> Response:
        arguments = {
            "action": "patch",
            "path": path or self.args.get("path", ""),
            "edits": self.args.get("edits", edits),
            "patch_text": self.args.get("patch_text", patch_text),
            "old_text": self.args.get("old_text", old_text),
            "new_text": self.args.get("new_text", new_text),
        }
        if "open_in_canvas" in self.args:
            arguments["open_in_canvas"] = self.args["open_in_canvas"]
        self.args = arguments
        return await super().execute(**arguments)
