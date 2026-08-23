from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_symbolics_compose_persists_only_nix_and_user_state():
    compose = (ROOT / "docker" / "symbolics" / "compose.yml").read_text(encoding="utf-8")
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


def test_symbolics_image_keeps_nix_binary_image_owned():
    dockerfile = (ROOT / "DockerfileLocal").read_text(encoding="utf-8")

    assert "apt-get install -y --no-install-recommends nix-bin" in dockerfile
    assert "ENV NIX_REMOTE=local" in dockerfile
    assert 'CMD ["/opt/a0-symbolics/initialize.sh"]' in dockerfile


def test_home_manager_seed_is_persistent_and_not_overwritten():
    initializer = (ROOT / "docker" / "symbolics" / "initialize.sh").read_text(encoding="utf-8")
    flake = (ROOT / "docker" / "symbolics" / "home-manager" / "flake.nix").read_text(encoding="utf-8")

    assert 'A0_HOME_MANAGER_DIR:-/a0/usr/home-manager' in initializer
    assert '[[ ! -e "$HM_DIR/$file" ]]' in initializer
    assert '[[ ! -e "$HM_DIR/flake.lock" ]]' in initializer
    assert "nixos-26.05" in flake
    assert "release-26.05" in flake
