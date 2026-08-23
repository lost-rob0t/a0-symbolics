from __future__ import annotations

from pathlib import Path

import pytest

from plugins._system_jobs.helpers import jobs


@pytest.fixture()
def isolated_jobs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "system-jobs"
    monkeypatch.setattr(jobs, "ROOT", root)
    monkeypatch.setattr(jobs, "JOBS_FILE", root / "jobs.json")
    monkeypatch.setattr(jobs, "SCRIPTS_DIR", root / "scripts")
    monkeypatch.setattr(jobs, "LOGS_DIR", root / "logs")
    monkeypatch.setattr(jobs, "_sync_crontab_unlocked", lambda _jobs: None)
    return root


def test_schedule_validation_accepts_cron_and_macros():
    assert jobs._validate_schedule("0 2 * * *") == "0 2 * * *"
    assert jobs._validate_schedule("@hourly") == "@hourly"
    with pytest.raises(ValueError):
        jobs._validate_schedule("every five minutes")


def test_managed_crontab_strip_preserves_unmanaged_entries():
    source = "\n".join(
        [
            "17 * * * * echo keep-me",
            jobs.BEGIN_MARKER,
            "0 2 * * * /bin/bash /old/job.sh",
            jobs.END_MARKER,
            "42 * * * * echo also-keep-me",
            "",
        ]
    )
    stripped = jobs._strip_managed_block(source)
    assert "keep-me" in stripped
    assert "also-keep-me" in stripped
    assert jobs.BEGIN_MARKER not in stripped
    assert "/old/job.sh" not in stripped


def test_save_job_writes_persistent_script(isolated_jobs: Path):
    job = jobs.save_job(
        name="hourly test",
        schedule="@hourly",
        script="printf 'ok\\n'",
        workdir="/tmp",
    )

    script_path = Path(job["script_path"])
    assert script_path.is_file()
    script = script_path.read_text(encoding="utf-8")
    assert "set -euo pipefail" in script
    assert "cd -- /tmp" in script
    assert "printf 'ok\\n'" in script
    assert jobs.JOBS_FILE.is_file()

    jobs.delete_job(job["id"])
    assert not script_path.exists()
    assert jobs.list_jobs() == []


def test_symbolics_runtime_uses_nix_cron_and_persistent_spool():
    project_root = Path(__file__).resolve().parents[3]
    home = (project_root / "docker" / "symbolics" / "home-manager" / "home.nix").read_text()
    initialize = (project_root / "docker" / "symbolics" / "initialize.sh").read_text()

    assert "    cron\n" in home
    assert 'cron_bin="/root/.nix-profile/bin/cron"' in initialize
    assert '"$SYSTEM_JOBS_DIR/cron/tabs"' in initialize
    assert 'ln -s "$SYSTEM_JOBS_DIR/cron" /var/cron' in initialize
    assert "command=$cron_bin -n" in initialize


def test_system_jobs_webui_and_skill_are_present():
    plugin_root = Path(__file__).resolve().parents[1]
    dashboard = (plugin_root / "webui" / "system-jobs.html").read_text()
    sidebar = (
        plugin_root
        / "extensions"
        / "webui"
        / "_sidebar-quick-actions-main-start"
        / "system-jobs-entry.html"
    ).read_text()
    skill = (plugin_root / "skills" / "system-jobs" / "SKILL.md").read_text()

    assert "New job" in dashboard
    assert "Run" in dashboard
    assert "Log" in dashboard
    assert "openModal('/plugins/_system_jobs/webui/system-jobs.html')" in sidebar
    assert "system_jobs" in skill
