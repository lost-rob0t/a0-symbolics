from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parents[1]


def test_symbolics_compose_example_persists_only_nix_and_user_state():
    compose = (ROOT / "docker" / "symbolics" / "compose.yml.example").read_text(encoding="utf-8")
    mount_lines = [
        line.strip()
        for line in compose.splitlines()
        if line.strip().startswith("- a0-symbolics-")
    ]

    assert mount_lines == [
        "- a0-symbolics-nix:/nix",
        "- a0-symbolics-usr:/a0/usr",
    ]
    assert ":/a0\n" not in compose


def test_symbolics_compose_bounds_memory_and_requires_live_smoke():
    compose = (ROOT / "docker" / "symbolics" / "compose.yml.example").read_text(encoding="utf-8")

    assert "    mem_limit: 8g\n" in compose
    assert "    memswap_limit: 8g\n" in compose
    assert '      PROLOG_RLM_ROOT: ""\n' in compose
    assert '      test: ["CMD", "/opt/a0-symbolics/healthcheck.sh"]\n' in compose


def test_symbolics_health_rejects_failed_supervisor_processes():
    healthcheck = (ROOT / "docker" / "symbolics" / "healthcheck.sh").read_text(
        encoding="utf-8"
    )

    assert "supervisorctl status" in healthcheck
    assert '$2 != "RUNNING"' in healthcheck


def test_symbolics_local_compose_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/docker/symbolics/compose.yml" in gitignore
    assert (ROOT / "docker" / "symbolics" / "compose.yml.example").is_file()


def test_symbolics_image_keeps_nix_binary_image_owned():
    dockerfile = (ROOT / "DockerfileLocal").read_text(encoding="utf-8")

    assert "apt-get install -y --no-install-recommends nix-bin" in dockerfile
    assert "ENV NIX_REMOTE=local" in dockerfile
    assert 'CMD ["/opt/a0-symbolics/initialize.sh"]' in dockerfile


def test_symbolics_image_installs_snapshot_desktop_before_nix_bin():
    dockerfile = (ROOT / "DockerfileLocal").read_text(encoding="utf-8")

    desktop_install = dockerfile.index("RUN bash /ins/install_additional.sh")
    nix_install = dockerfile.index(
        "apt-get install -y --no-install-recommends nix-bin"
    )

    assert desktop_install < nix_install


def test_home_manager_seed_is_persistent_and_not_overwritten():
    initializer = (ROOT / "docker" / "symbolics" / "initialize.sh").read_text(encoding="utf-8")
    flake = (ROOT / "docker" / "symbolics" / "home-manager" / "flake.nix").read_text(encoding="utf-8")

    assert 'A0_HOME_MANAGER_DIR:-/a0/usr/home-manager' in initializer
    assert '[[ ! -e "$HM_DIR/$file" ]]' in initializer
    assert '[[ ! -e "$HM_DIR/flake.lock" ]]' in initializer
    assert "nixos-26.05" in flake
    assert "release-26.05" in flake


def test_symbolics_initializer_defaults_container_user():
    initializer = (ROOT / "docker" / "symbolics" / "initialize.sh").read_text(encoding="utf-8")

    assert 'export USER="${USER:-root}"' in initializer


def test_home_manager_seed_uses_current_swi_prolog_attribute():
    home_nix = (ROOT / "docker" / "symbolics" / "home-manager" / "home.nix").read_text(encoding="utf-8")

    assert "    swi-prolog\n" in home_nix
    assert "    swipl\n" not in home_nix


def test_system_cron_rewrite_does_not_expand_bash_argument_count():
    initializer = (ROOT / "docker" / "symbolics" / "initialize.sh").read_text(encoding="utf-8")

    assert '/usr/sbin/cron -f\\$#command=' in initializer


def test_initializer_activates_pinned_prolog_rlm_and_generates_health_evidence():
    initializer = (ROOT / "docker" / "symbolics" / "initialize.sh").read_text(encoding="utf-8")

    assert 'nix build "$source_root#prolog-rlm" --no-link --print-out-paths' in initializer
    assert 'export SWIPL_PACK_PATH="$prolog_rlm/share/swi-prolog/pack' in initializer
    assert "/nix/var/nix/gcroots/a0-symbolics-prolog-rlm" in initializer
    assert '"$prolog_rlm/share/swi-prolog/pack/prolog_rlm" "$pack_dir/prolog_rlm"' in initializer
    assert '/opt/a0-symbolics/smoke.sh /a0 > "$smoke_tmp"' in initializer
    assert 'mv "$smoke_tmp" /run/a0-symbolics/smoke.json' in initializer


def test_symbolics_operator_scripts_are_executable_and_bound_build_memory():
    launcher = ROOT / "scripts" / "symbolics"
    text = launcher.read_text(encoding="utf-8")

    assert launcher.stat().st_mode & stat.S_IXUSR
    assert 'A0_SYMBOLICS_BUILD_MEMORY:-8g' in text
    assert 'compose build --memory "$BUILD_MEMORY"' in text
    assert 'compose build --pull --memory "$BUILD_MEMORY"' in text

    for name in ("up", "down", "status", "logs", "update", "verify"):
        wrapper = ROOT / "scripts" / name
        assert wrapper.stat().st_mode & stat.S_IXUSR
        assert 'exec "$(dirname "${BASH_SOURCE[0]}")/symbolics"' in wrapper.read_text(encoding="utf-8")


def test_root_launch_uses_stable_symbolics_compose_project():
    launcher = ROOT / "launch.sh"
    text = launcher.read_text(encoding="utf-8")

    assert launcher.stat().st_mode & stat.S_IXUSR
    assert 'A0_SYMBOLICS_PROJECT:-a0-symbolics' in text
    assert "docker compose --project-name" in text
