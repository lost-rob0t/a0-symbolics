import sys
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PLUGIN_DIR = PROJECT_ROOT / "plugins" / "_a0s_prompts"

# plugin-relative path -> upstream-owned source it replaces
OVERRIDES = {
    "prompts/agent.system.main.solving.md": "prompts/agent.system.main.solving.md",
    "prompts/agent.system.tool.code_exe.md": "plugins/_code_execution/prompts/agent.system.tool.code_exe.md",
    "agents/agent0/prompts/agent.system.main.role.md": "agents/agent0/prompts/agent.system.main.role.md",
    "agents/developer/prompts/agent.system.main.specifics.md": "agents/developer/prompts/agent.system.main.specifics.md",
    "agents/hacker/prompts/agent.system.main.specifics.md": "agents/hacker/prompts/agent.system.main.specifics.md",
    "agents/researcher/prompts/agent.system.main.specifics.md": "agents/researcher/prompts/agent.system.main.specifics.md",
}


def _plugin_file(relative: str) -> Path:
    return PLUGIN_DIR / relative


def _framework_file(relative: str) -> Path:
    return PROJECT_ROOT / relative


@pytest.mark.parametrize("relative", sorted(OVERRIDES))
def test_overlay_ships_every_overridden_prompt(relative):
    assert _plugin_file(relative).exists(), relative


@pytest.mark.parametrize("relative", sorted(OVERRIDES))
def test_overlay_files_differ_from_upstream_sources(relative):
    """The overlay must actually carry Symbolics text, not a no-op copy."""
    plugin_text = _plugin_file(relative).read_text(encoding="utf-8")
    framework_text = _framework_file(OVERRIDES[relative]).read_text(encoding="utf-8")
    assert plugin_text != framework_text, relative


def test_overlay_plugin_manifest_is_always_enabled():
    manifest = yaml.safe_load(_plugin_file("plugin.yaml").read_text(encoding="utf-8"))
    assert manifest["name"] == "_a0s_prompts"
    assert manifest["always_enabled"] is True
    assert not (PLUGIN_DIR / "extensions").exists(), "prompt overlay plugin must stay ownership-only"


def test_framework_prompts_no_longer_carry_symbolics_rewrites():
    """Upstream-owned prompt files stay clean; Symbolics text lives in the overlay."""
    role = _framework_file("agents/agent0/prompts/agent.system.main.role.md").read_text(encoding="utf-8")
    assert "surface concerns as findings" not in role

    overlay_role = _plugin_file("agents/agent0/prompts/agent.system.main.role.md").read_text(encoding="utf-8")
    assert "surface concerns as findings" in overlay_role

    developer = _framework_file("agents/developer/prompts/agent.system.main.specifics.md").read_text(encoding="utf-8")
    assert "Completion Standard" not in developer

    overlay_developer = _plugin_file("agents/developer/prompts/agent.system.main.specifics.md").read_text(encoding="utf-8")
    assert "Completion Standard" in overlay_developer

    code_exe = _framework_file("plugins/_code_execution/prompts/agent.system.tool.code_exe.md").read_text(encoding="utf-8")
    overlay_code_exe = _plugin_file("prompts/agent.system.tool.code_exe.md").read_text(encoding="utf-8")
    assert code_exe != overlay_code_exe


def test_hacker_overlay_references_cyber_behavior_guide():
    overlay_hacker = _plugin_file("agents/hacker/prompts/agent.system.main.specifics.md").read_text(encoding="utf-8")
    assert "security engineer" in overlay_hacker.lower()
    assert (PROJECT_ROOT / "docs" / "guides" / "cyber-task-behavior.md").exists()