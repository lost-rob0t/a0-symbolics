from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _scalar(path: str, key: str):
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(key)}:\s*([^#\n]+)", text, re.MULTILINE)
    assert match, f"missing {key} in {path}"
    raw = match.group(1).strip()
    if raw in {"true", "false"}:
        return raw == "true"
    try:
        return int(raw)
    except ValueError:
        return float(raw)


def test_promptinclude_defaults_are_bounded():
    path = "plugins/_promptinclude/default_config.yaml"
    assert _scalar(path, "max_depth") == 3
    assert _scalar(path, "max_file_tokens") == 750
    assert _scalar(path, "max_file_count") == 8
    assert _scalar(path, "max_total_tokens") == 1500


def test_promptinclude_runtime_fallbacks_match_bounded_defaults():
    text = (
        ROOT
        / "plugins/_promptinclude/extensions/python/system_prompt/_16_promptinclude.py"
    ).read_text(encoding="utf-8")
    assert "DEFAULT_MAX_DEPTH = 3" in text
    assert "DEFAULT_MAX_FILE_TOKENS = 750" in text
    assert "DEFAULT_MAX_FILE_COUNT = 8" in text
    assert "DEFAULT_MAX_TOTAL_TOKENS = 1500" in text


def test_memory_recall_defaults_limit_ambient_context():
    path = "plugins/_memory/default_config.yaml"
    assert _scalar(path, "project_memory_isolation") is True
    assert _scalar(path, "memory_recall_history_len") == 4000
    assert _scalar(path, "memory_recall_memories_max_search") == 8
    assert _scalar(path, "memory_recall_solutions_max_search") == 4
    assert _scalar(path, "memory_recall_memories_max_result") == 3
    assert _scalar(path, "memory_recall_solutions_max_result") == 1
    assert _scalar(path, "memory_recall_similarity_threshold") == 0.75


def test_solving_prompt_is_compact_and_rage_free():
    text = (ROOT / "prompts/agent.system.main.solving.md").read_text(encoding="utf-8")
    assert "explain each step in thoughts" not in text.lower()
    assert "RAGE" not in text
    assert len(text) < 1400
