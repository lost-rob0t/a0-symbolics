import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.modules["giturlparse"] = __import__("types").SimpleNamespace(parse=lambda *args, **kwargs: None)

from helpers import self_update, symbolics_release


DISTRIBUTION_REPO = "https://github.com/lost-rob0t/a0-symbolics.git"
UPSTREAM_REPO = "https://github.com/agent0ai/agent-zero.git"


def load_self_update_manager():
    manager_path = (
        PROJECT_ROOT / "docker" / "run" / "fs" / "exe" / "self_update_manager.py"
    )
    spec = importlib.util.spec_from_file_location("test_self_update_policy_manager", manager_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def clean_update_env(monkeypatch):
    monkeypatch.delenv(self_update.UPDATE_SOURCE_OVERRIDE_ENV, raising=False)
    monkeypatch.delenv(self_update.UPSTREAM_SOURCE_OVERRIDE_ENV, raising=False)


def test_update_source_defaults_to_distribution_remotes(monkeypatch):
    monkeypatch.setattr(
        symbolics_release,
        "get_distribution_repo_urls",
        lambda metadata=None: [DISTRIBUTION_REPO],
    )

    urls = self_update.get_update_source_urls()

    assert urls == [DISTRIBUTION_REPO]
    assert all(not symbolics_release.is_upstream_repo_url(url) for url in urls)


def test_update_source_refuses_raw_upstream_override(monkeypatch):
    monkeypatch.setattr(
        symbolics_release,
        "get_distribution_repo_urls",
        lambda metadata=None: [],
    )
    monkeypatch.setenv(self_update.UPDATE_SOURCE_OVERRIDE_ENV, UPSTREAM_REPO)

    with pytest.raises(RuntimeError, match="must self-update from the Symbolics distribution"):
        self_update.get_update_source_urls()


def test_update_source_allows_upstream_override_only_for_development(monkeypatch):
    monkeypatch.setattr(
        symbolics_release,
        "get_distribution_repo_urls",
        lambda metadata=None: [],
    )
    monkeypatch.setenv(self_update.UPDATE_SOURCE_OVERRIDE_ENV, UPSTREAM_REPO)
    monkeypatch.setenv(self_update.UPSTREAM_SOURCE_OVERRIDE_ENV, "1")

    urls = self_update.get_update_source_urls()

    assert urls == [UPSTREAM_REPO]


def test_update_source_refuses_when_unconfigured(monkeypatch):
    monkeypatch.setattr(
        symbolics_release,
        "get_distribution_repo_urls",
        lambda metadata=None: [],
    )

    with pytest.raises(RuntimeError, match="No a0-symbolics update source is configured"):
        self_update.get_update_source_urls()


def test_manager_update_source_requires_metadata(tmp_path):
    manager = load_self_update_manager()

    with pytest.raises(RuntimeError, match="No a0-symbolics update source is configured"):
        manager.get_update_source_urls(tmp_path)


def test_manager_update_source_refuses_raw_upstream(tmp_path):
    manager = load_self_update_manager()
    (tmp_path / "maint").mkdir()
    (tmp_path / "maint" / "upstream.toml").write_text(
        "[distribution]\n"
        f'repository = "{UPSTREAM_REPO}"\n',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="raw Agent Zero upstream"):
        manager.get_update_source_urls(tmp_path)


def test_manager_update_source_reads_distribution_metadata(tmp_path):
    manager = load_self_update_manager()
    (tmp_path / "maint").mkdir()
    (tmp_path / "maint" / "upstream.toml").write_text(
        "[distribution]\n"
        f'repository = "{DISTRIBUTION_REPO}"\n',
        encoding="utf-8",
    )

    urls = manager.get_update_source_urls(tmp_path)

    assert urls == [DISTRIBUTION_REPO]


def _init_repo_with_marker(root: Path, with_marker: bool) -> Path:
    repo = root / "repo"
    repo.mkdir()
    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    git("init", "--quiet")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    (repo / "run_ui.py").write_text("# app\n", encoding="utf-8")
    if with_marker:
        (repo / "maint").mkdir()
        (repo / "maint" / "upstream.toml").write_text("[upstream]\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "--quiet", "-m", "target")
    return repo


def test_manager_marker_guard_refuses_target_without_distribution_marker(tmp_path):
    manager = load_self_update_manager()
    repo = _init_repo_with_marker(tmp_path, with_marker=False)

    with pytest.raises(RuntimeError, match="distribution marker"):
        manager.require_distribution_marker(repo, "HEAD", manager.NullLogger())


def test_manager_marker_guard_accepts_distribution_target(tmp_path):
    manager = load_self_update_manager()
    repo = _init_repo_with_marker(tmp_path, with_marker=True)
    messages = []

    class ListLogger:
        def log(self, message=""):
            messages.append(message)

    manager.require_distribution_marker(repo, "HEAD", ListLogger())

    assert any("distribution marker" in message for message in messages)


def test_manager_replay_refuses_upstream_target_without_marker(tmp_path, monkeypatch):
    """End-to-end: a target fetched from a repo without the marker must refuse to resolve."""
    manager = load_self_update_manager()
    upstream = tmp_path / "upstream"
    upstream.mkdir()

    def git(repo: Path, *args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

    git(upstream, "init", "--quiet", "-b", "main")
    git(upstream, "config", "user.email", "test@example.com")
    git(upstream, "config", "user.name", "Test")
    (upstream / "run_ui.py").write_text("# raw upstream\n", encoding="utf-8")
    git(upstream, "add", "-A")
    git(upstream, "commit", "--quiet", "-m", "upstream release")
    git(upstream, "tag", "a0s-v9.9.9")

    target = _init_repo_with_marker(tmp_path, with_marker=True)
    monkeypatch.setenv(self_update.UPDATE_SOURCE_OVERRIDE_ENV, str(upstream))

    with pytest.raises(RuntimeError, match="distribution marker"):
        manager.resolve_requested_target(
            target,
            "main",
            "a0s-v9.9.9",
            "a0s-v0.1",
            manager.NullLogger(),
        )


def test_durable_manager_policy_is_declared_disabled_by_default():
    manager = load_self_update_manager()

    assert manager.UPSTREAM_REPO_SIGNATURE == "agent0ai/agent-zero"
    assert manager.DISTRIBUTION_METADATA_RELPATH == "maint/upstream.toml"
    assert manager.UPSTREAM_REPO_URL.rstrip("/").endswith("agent-zero.git")


def test_metadata_declares_immutable_upstream_base():
    metadata = symbolics_release.load_maintenance_metadata()
    upstream = symbolics_release.get_upstream_info(metadata)

    assert upstream["repository"] == UPSTREAM_REPO
    assert upstream["tag"].startswith("v")
    assert len(upstream["commit"]) == 40


def test_symbolics_release_identity_tracks_upstream_base():
    metadata = symbolics_release.load_maintenance_metadata()

    version = symbolics_release.get_symbolics_version(metadata)
    parsed = symbolics_release.parse_release_tag(version, metadata)

    assert version == f"a0s-{symbolics_release.get_upstream_info(metadata)['tag']}.{metadata['distribution']['series']}"
    assert parsed is not None


def test_parse_release_tag_rejects_upstream_tags():
    assert symbolics_release.parse_release_tag("v2.12") is None
    assert symbolics_release.parse_release_tag("a0s-v2.12.0") == (2, 12, 0)