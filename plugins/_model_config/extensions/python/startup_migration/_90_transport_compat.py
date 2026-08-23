from __future__ import annotations

from helpers.extension import Extension
from plugins._model_config.helpers.transport_compat import install_transport_compat


class ModelTransportCompatibility(Extension):
    def execute(self, **kwargs):
        install_transport_compat()
