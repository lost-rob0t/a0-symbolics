from helpers.extension import Extension
from plugins._symbolics.helpers.mode import sync_runtime_mode


class SymbolicsRuntimeMode(Extension):
    def execute(self, **kwargs):
        sync_runtime_mode()
