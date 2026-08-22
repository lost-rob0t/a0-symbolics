from __future__ import annotations

import json
import shutil
from pathlib import Path

from helpers.extension import Extension
from helpers.print_style import PrintStyle
from plugins._model_config.helpers import model_config


CANONICAL_PRESETS_FILE = "lost_robot_presets.yaml"
MARKER_FILE = "lost_robot_preset_pack_v1.json"
BACKUP_SUFFIX = ".pre-lost-robot-pack.bak"
PACK_VERSION = 1


def _canonical_presets_path() -> Path:
    return Path(model_config._get_fallback_presets_path()).with_name(
        CANONICAL_PRESETS_FILE
    )


class ApplyLostRobotPresetPack(Extension):
    """Apply the fork's canonical preset pack once, then leave user edits alone."""

    def execute(self, **kwargs):
        presets_path = Path(model_config._get_presets_path())
        marker_path = presets_path.with_name(MARKER_FILE)
        if marker_path.exists():
            return "existing"

        try:
            canonical = model_config.parse_preset_collection(
                _canonical_presets_path().read_text(encoding="utf-8")
            )
        except Exception as exc:
            PrintStyle.error(f"Canonical model preset pack is invalid: {exc}")
            return "error"

        presets_path.parent.mkdir(parents=True, exist_ok=True)

        current = None
        if presets_path.exists():
            try:
                current = model_config.parse_preset_collection(
                    presets_path.read_text(encoding="utf-8")
                )
            except Exception:
                current = None

        if current != canonical:
            if presets_path.exists():
                backup_path = Path(f"{presets_path}{BACKUP_SUFFIX}")
                if not backup_path.exists():
                    shutil.copy2(presets_path, backup_path)
            try:
                model_config.save_presets(canonical)
            except Exception as exc:
                PrintStyle.error(f"Could not apply canonical model preset pack: {exc}")
                return "error"
            result = "updated"
        else:
            result = "current"

        marker_path.write_text(
            json.dumps(
                {
                    "version": PACK_VERSION,
                    "presets": [preset["name"] for preset in canonical],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        PrintStyle.info("Applied canonical Agent Zero model preset pack.")
        return result
