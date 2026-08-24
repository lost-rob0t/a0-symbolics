from typing import Any

from helpers import files
from helpers.extension import Extension


class CompactToolExamples(Extension):
    def execute(self, data: dict[str, Any], **kwargs: Any) -> None:
        if data.get("exception") is None and isinstance(data.get("result"), str):
            compact = files.remove_fenced_blocks(data["result"], "json")
            data["result"] = "\n".join(
                line
                for line in compact.splitlines()
                if not line.lstrip().startswith("Input schema for tool_args:")
            )
