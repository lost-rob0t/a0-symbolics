import importlib.util
import sys
import tomllib
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_upstream_sync():
    script = PROJECT_ROOT / "scripts" / "upstream-sync"
    loader = SourceFileLoader("upstream_sync_test_module", str(script))
    spec = importlib.util.spec_from_loader("upstream_sync_test_module", loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


upsync = load_upstream_sync()


def test_metadata_declares_immutable_upstream_commit():
    meta = upsync.load_metadata()
    upstream = upsync.upstream_ref(meta)

    assert upstream["repository"].endswith("agent-zero.git")
    assert upstream["tag"].startswith("v")
    assert len(upstream["commit"]) == 40
    distribution = meta["distribution"]
    assert distribution["release_prefix"] == "a0s-"
    assert set(distribution["repository"]) > set()
    assert meta["selfupdate"]["allow_upstream_source"] is False


def test_classify_fork_delta_prefers_explicit_notes(monkeypatch):
    assert upsync.classify_fork_delta("agent.py", "deadbeef")[0] == "unavoidable-core-patch"
    assert upsync.classify_fork_delta("helpers/ws.py", "deadbeef")[0] == "obsolete"
    assert upsync.classify_fork_delta(
        "prompts/agent.system.main.solving.md", "deadbeef"
    )[0] == "plugin"


def test_classify_fork_delta_uses_path_heuristics_for_additions(monkeypatch):
    monkeypatch.setattr(upsync, "file_exists_in", lambda ref, path: False)

    assert upsync.classify_fork_delta("plugins/_new/plugin.yaml", "deadbeef")[0] == "plugin"
    assert upsync.classify_fork_delta("extensions/python/system_prompt/_99_x.py", "deadbeef")[0] == "extension"
    assert upsync.classify_fork_delta("nix/python-env.nix", "deadbeef")[0] == "packaging"
    assert upsync.classify_fork_delta("android/app/build.gradle.kts", "deadbeef")[0] == "packaging"
    assert upsync.classify_fork_delta("tests/test_new_symbolic.py", "deadbeef")[0] == "symbolic-runtime"


def test_classify_fork_delta_flags_upstream_file_modifications(monkeypatch):
    monkeypatch.setattr(upsync, "file_exists_in", lambda ref, path: True)

    assert upsync.classify_fork_delta("helpers/history.py", "deadbeef")[0] == "unavoidable-core-patch"
    assert upsync.classify_fork_delta("initialize.py", "deadbeef")[0] == "unavoidable-core-patch"


def test_write_fork_surface_toml_is_parseable_and_complete(tmp_path):
    surface = {
        "base": "a" * 40,
        "ref": "b" * 40,
        "files_changed": 2,
        "files_added": 1,
        "upstream_owned_modified": 1,
        "upstream_owned_files": ["agent.py"],
        "loc_added": 10,
        "loc_removed": 2,
        "core_patch_loc": 5,
        "core_patches": 1,
        "hotspots": ["agent.py"],
        "counts": {"unavoidable-core-patch": 1, "plugin": 1},
        "entries": [
            {"path": "agent.py", "class": "unavoidable-core-patch", "note": "name map", "added": 3, "removed": 2},
            {"path": "plugins/_new/plugin.yaml", "class": "plugin", "note": "new", "added": 1, "removed": 0},
        ],
    }

    output = upsync.write_fork_surface_toml(surface)
    data = tomllib.loads(output)

    assert data["summary"]["core_patches"] == 1
    assert data["counts"]["plugin"] == 1
    assert data["upstream_owned_files"]["agent.py"]["class"] == "unavoidable-core-patch"


def test_hotspot_files_are_tracked():
    for path in ("agent.py", "models.py", "helpers/extract_tools.py", "helpers/self_update.py"):
        assert path in upsync.HOTSPOT_FILES


def test_core_patch_notes_cover_all_hotspots_declared():
    declared = upsync.HOTSPOT_FILES & set(upsync.CORE_PATCH_NOTES)
    assert declared == {
        "agent.py",
        "models.py",
        "helpers/extract_tools.py",
        "helpers/litellm_transport.py",
        "helpers/self_update.py",
        "helpers/state_snapshot.py",
        "webui/js/messages.js",
        "conf/model_providers.yaml",
    }