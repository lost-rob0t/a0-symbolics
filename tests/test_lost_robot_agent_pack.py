from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRESET_PACK = (
    PROJECT_ROOT / "plugins" / "_model_config" / "lost_robot_presets.yaml"
)


def _load_pack() -> list[dict]:
    return yaml.safe_load(PRESET_PACK.read_text(encoding="utf-8"))


def test_lost_robot_model_pack_has_only_three_unique_stacks():
    presets = _load_pack()

    assert [preset["name"] for preset in presets] == [
        "Default",
        "GLM 5.3 MAX / Luna 5.6 MAX",
        "Luna 5.6 MAX / Gemini Flash-Lite",
    ]

    effective_pairs = [
        (preset["chat"]["name"], preset["utility"]["name"])
        for preset in presets
    ]
    assert len(effective_pairs) == len(set(effective_pairs)) == 3

    assert effective_pairs == [
        ("anthropic/claude-fable-5", "openai/gpt-5.6-luna"),
        ("z-ai/glm-5.3", "openai/gpt-5.6-luna"),
        ("openai/gpt-5.6-luna", "google/gemini-3.1-flash-lite"),
    ]


def test_lost_robot_model_pack_applies_requested_reasoning_effort():
    presets = _load_pack()
    default, glm, luna = presets

    assert default["utility"]["kwargs"]["reasoning"]["effort"] == "max"
    assert default["chat"]["kwargs"] == {}
    assert glm["chat"]["kwargs"]["reasoning"]["effort"] == "max"
    assert glm["utility"]["kwargs"]["reasoning"]["effort"] == "max"
    assert luna["chat"]["kwargs"]["reasoning"]["effort"] == "max"
    assert luna["utility"]["kwargs"] == {}


def test_lost_robot_profiles_are_thin_and_distinct():
    expected = {
        "starintel-adar": "StarIntel ADAR",
        "rage-worker": "RAGE Worker",
        "zara": "Zara",
        "social-automation": "Social Media Automation",
    }
    prompts = []

    for slug, title in expected.items():
        profile_dir = PROJECT_ROOT / "agents" / slug
        metadata = yaml.safe_load(
            (profile_dir / "agent.yaml").read_text(encoding="utf-8")
        )
        prompt_path = (
            profile_dir / "prompts" / "agent.system.main.specifics.md"
        )
        prompt = prompt_path.read_text(encoding="utf-8")

        assert metadata["title"] == title
        assert metadata["description"]
        assert metadata["context"]
        assert 100 < len(prompt) < 5000
        prompts.append(prompt)

    assert len(prompts) == len(set(prompts))


def test_lost_robot_preset_pack_migration_runs_once_and_backs_up(monkeypatch, tmp_path):
    from plugins._model_config.extensions.python.startup_migration._30_apply_lost_robot_preset_pack import (
        ApplyLostRobotPresetPack,
        BACKUP_SUFFIX,
        MARKER_FILE,
    )
    from plugins._model_config.helpers import model_config

    presets_path = tmp_path / "usr" / "plugins" / "_model_config" / "presets.yaml"
    presets_path.parent.mkdir(parents=True)
    old_text = """
- name: Default
  chat: {provider: openrouter, name: old-chat}
  utility: {provider: openrouter, name: old-utility}
  embedding: {provider: huggingface, name: old-embedding}
- name: Duplicate A
  chat: {provider: openrouter, name: same-chat}
- name: Duplicate B
  chat: {provider: openrouter, name: same-chat}
""".lstrip()
    presets_path.write_text(old_text, encoding="utf-8")

    monkeypatch.setattr(
        model_config,
        "_get_presets_path",
        lambda project_name=None: str(presets_path),
    )

    migration = ApplyLostRobotPresetPack(agent=None)
    assert migration.execute() == "updated"

    saved = yaml.safe_load(presets_path.read_text(encoding="utf-8"))
    assert [preset["name"] for preset in saved] == [
        "Default",
        "GLM 5.3 MAX / Luna 5.6 MAX",
        "Luna 5.6 MAX / Gemini Flash-Lite",
    ]
    assert Path(f"{presets_path}{BACKUP_SUFFIX}").read_text(encoding="utf-8") == old_text
    assert (presets_path.parent / MARKER_FILE).exists()

    edited = presets_path.read_text(encoding="utf-8") + "# user edit after migration\n"
    presets_path.write_text(edited, encoding="utf-8")
    assert migration.execute() == "existing"
    assert presets_path.read_text(encoding="utf-8") == edited
