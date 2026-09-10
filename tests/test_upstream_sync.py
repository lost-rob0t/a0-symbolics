import argparse
import importlib.util
import json
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


OLD_METADATA = """# Canonical upstream base and distribution identity for a0-symbolics.
#
# The upstream commit is immutable and authoritative. Never identify the base
# by a mutable branch name. This file is updated only by scripts/upstream-sync
# during an upstream synchronization, never by hand during normal work.

[upstream]
repository = "https://github.com/agent0ai/agent-zero.git"
tag = "v2.10"
commit = "%s"

[distribution]
name = "a0-symbolics"
# Release identity: a0s-<upstream-tag>.<series>, e.g. a0s-v2.10.1.
release_prefix = "a0s-"
series = 1

[selfupdate]
allow_upstream_source = false
""" % ("b" * 40)


def test_parse_tag_version_compares_numerically():
    assert upsync.parse_tag_version("v2.10") == (2, 10)
    assert upsync.parse_tag_version("v2.12") > upsync.parse_tag_version("v2.10")
    assert upsync.parse_tag_version("v2.9") < upsync.parse_tag_version("v2.10")
    assert upsync.parse_tag_version("main") is None
    assert upsync.parse_tag_version("") is None


def test_rewrite_upstream_metadata_changes_only_upstream_table():
    new_commit = "c" * 40
    updated = upsync.rewrite_upstream_metadata(OLD_METADATA, "v2.12", new_commit)

    data = tomllib.loads(updated)
    assert data["upstream"]["tag"] == "v2.12"
    assert data["upstream"]["commit"] == new_commit
    assert data["distribution"]["series"] == 1
    assert data["distribution"]["release_prefix"] == "a0s-"
    assert data["selfupdate"]["allow_upstream_source"] is False
    assert 'commit = "%s"' % ("b" * 40) not in updated


def test_replace_identity_example_updates_e_g_comment():
    updated = upsync.replace_identity_example(OLD_METADATA, "a0s-", "a0s-v2.12.1")
    assert "e.g. a0s-v2.12.1." in updated
    assert "e.g. a0s-v2.10.1." not in updated


def _write_replay_fixture(tmp_path, completed=True, branch="a0s-replay-2-12"):
    state_dir = tmp_path / "maint" / "reports" / "prepare-v2.12"
    state_dir.mkdir(parents=True)
    state = {"replayed": [], "tag": "v2.12", "completed": completed, "branch": branch}
    (state_dir / "state.json").write_text(json.dumps(state))
    worktree = tmp_path / "worktree"
    (worktree / ".git").mkdir(parents=True)
    return state_dir, worktree


def test_validate_promotion_state_accepts_completed_replay(tmp_path, monkeypatch):
    state_dir, worktree = _write_replay_fixture(tmp_path)
    monkeypatch.setattr(upsync, "run_git", lambda *a, **k: {
        ("rev-parse", "--abbrev-ref", "HEAD"): "a0s-replay-2-12",
        ("status", "--porcelain", "--untracked-files=no"): "",
        ("rev-parse", "HEAD"): "d" * 40,
    }.get(tuple(a), ""))

    checks = upsync.validate_promotion_state("v2.12", state_dir, worktree)
    assert checks["branch"] == "a0s-replay-2-12"
    assert checks["head"] == "d" * 40


def test_validate_promotion_state_refuses_incomplete_replay(tmp_path):
    state_dir, worktree = _write_replay_fixture(tmp_path, completed=False)
    with pytest.raises(SystemExit, match="not completed"):
        upsync.validate_promotion_state("v2.12", state_dir, worktree)


def test_validate_promotion_state_refuses_missing_replay(tmp_path):
    with pytest.raises(SystemExit, match="No replay state"):
        upsync.validate_promotion_state("v2.12", tmp_path / "reports", tmp_path / "wt")


def test_validate_promotion_state_refuses_wrong_branch(tmp_path, monkeypatch):
    state_dir, worktree = _write_replay_fixture(tmp_path)
    monkeypatch.setattr(upsync, "run_git", lambda *a, **k: "some-other-branch" if a[0] == "rev-parse" else "")

    with pytest.raises(SystemExit, match="expected"):
        upsync.validate_promotion_state("v2.12", state_dir, worktree)


def test_validate_promotion_state_refuses_dirty_worktree(tmp_path, monkeypatch):
    state_dir, worktree = _write_replay_fixture(tmp_path)

    def fake_run_git(*a, **k):
        if a[0] == "status":
            return " M scripts/upstream-sync"
        if a[:2] == ("rev-parse", "--abbrev-ref"):
            return "a0s-replay-2-12"
        return "d" * 40

    monkeypatch.setattr(upsync, "run_git", fake_run_git)
    with pytest.raises(SystemExit, match="dirty"):
        upsync.validate_promotion_state("v2.12", state_dir, worktree)


def test_promotion_refuses_backwards_or_equal_base(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(upsync, "load_metadata", lambda path=None: {
        "upstream": {"repository": "https://github.com/agent0ai/agent-zero.git",
                     "tag": "v2.12", "commit": "c" * 40},
        "distribution": {"release_prefix": "a0s-", "series": 1},
    })
    monkeypatch.setattr(upsync, "resolve_tag", lambda tag: "c" * 40)
    monkeypatch.setattr(upsync, "is_dirty", lambda: False)
    monkeypatch.setattr(upsync, "REPO_ROOT", tmp_path)

    upsync.cmd_promote(argparse.Namespace(tag="v2.12", repo=""))
    assert "already promoted" in capsys.readouterr().out

    monkeypatch.setattr(upsync, "resolve_tag", lambda tag: "e" * 40)
    with pytest.raises(SystemExit, match="backwards"):
        upsync.cmd_promote(argparse.Namespace(tag="v2.10", repo=""))


def test_promotion_refuses_head_without_upstream_commit(tmp_path, monkeypatch):
    state_dir, worktree = _write_replay_fixture(tmp_path)
    monkeypatch.setattr(upsync, "load_metadata", lambda path=None: {
        "upstream": {"repository": "https://github.com/agent0ai/agent-zero.git",
                     "tag": "v2.10", "commit": "b" * 40},
        "distribution": {"release_prefix": "a0s-", "series": 1},
    })
    monkeypatch.setattr(upsync, "resolve_tag", lambda tag: "c" * 40)
    monkeypatch.setattr(upsync, "is_dirty", lambda: False)
    monkeypatch.setattr(upsync, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(upsync, "MAINT_DIR", tmp_path / "maint")
    monkeypatch.setattr(upsync, "validate_promotion_state",
                        lambda tag, sd, wt: {"branch": "a0s-replay-2-12", "head": "d" * 40})
    monkeypatch.setattr(upsync, "git_ok", lambda *a, **k: False)

    with pytest.raises(SystemExit, match="does not contain"):
        upsync.cmd_promote(argparse.Namespace(tag="v2.12", repo=str(worktree)))


def test_apply_promotion_writes_metadata_fork_surface_and_evidence(tmp_path, monkeypatch):
    worktree = tmp_path / "worktree"
    (worktree / "maint").mkdir(parents=True)
    (worktree / "maint" / "upstream.toml").write_text(OLD_METADATA)
    state_dir = tmp_path / "maint" / "reports" / "prepare-v2.12"
    state_dir.mkdir(parents=True)

    surface = {
        "base": "c" * 40, "ref": "d" * 40, "files_changed": 2, "files_added": 1,
        "upstream_owned_modified": 1, "loc_added": 10, "loc_removed": 2,
        "core_patch_loc": 5, "core_patches": 1,
        "hotspots": [], "counts": {}, "entries": [],
        "upstream_owned_files": [],
    }
    monkeypatch.setattr(upsync, "fork_surface", lambda base, ref: surface)
    monkeypatch.setattr(upsync, "run_git", lambda *a, **k: "f" * 40 if a[0] == "rev-parse" else "")
    monkeypatch.setattr(upsync, "load_metadata",
                        lambda path=None: {"upstream": {"tag": "v2.10", "commit": "b" * 40}})
    monkeypatch.setattr(upsync, "REPO_ROOT", tmp_path)

    meta = {
        "upstream": {"tag": "v2.10", "commit": "b" * 40},
        "distribution": {"release_prefix": "a0s-", "series": 1},
    }
    checks = {"branch": "a0s-replay-2-12", "head": "d" * 40}
    summary = upsync.apply_promotion(
        worktree, "v2.12", "c" * 40, "b" * 40, meta, checks, state_dir)

    metadata_text = (worktree / "maint" / "upstream.toml").read_text()
    data = tomllib.loads(metadata_text)
    assert data["upstream"]["tag"] == "v2.12"
    assert data["upstream"]["commit"] == "c" * 40
    assert data["distribution"]["series"] == 1
    assert data["selfupdate"]["allow_upstream_source"] is False
    assert "e.g. a0s-v2.12.1." in metadata_text
    surface_toml = tomllib.loads((worktree / "maint" / "fork-surface.toml").read_text())
    assert surface_toml["summary"]["core_patch_loc"] == 5
    evidence = json.loads((state_dir / "promotion.json").read_text())
    assert evidence["old_base"] == {"tag": "v2.10", "commit": "b" * 40}
    assert evidence["new_base"]["tag"] == "v2.12"
    assert evidence["replay_branch"] == "a0s-replay-2-12"
    assert summary["promotion_commit"] == "f" * 40