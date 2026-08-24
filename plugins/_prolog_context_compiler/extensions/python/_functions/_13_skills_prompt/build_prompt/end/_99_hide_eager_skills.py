from helpers.extension import Extension
from plugins._prolog_context_compiler.helpers.bridge import compiler_enabled


class HideEagerSkillCatalog(Extension):
    def execute(self, data: dict, **kwargs) -> None:
        if (
            self.agent
            and compiler_enabled(self.agent)
            and data.get("exception") is None
        ):
            data["result"] = ""
