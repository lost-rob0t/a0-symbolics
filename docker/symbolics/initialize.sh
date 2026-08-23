#!/usr/bin/env bash
set -euo pipefail

readonly HM_DIR="${A0_HOME_MANAGER_DIR:-/a0/usr/home-manager}"
readonly HM_SEED_DIR="/opt/a0-symbolics/home-manager"

seed_home_manager() {
  mkdir -p "$HM_DIR"

  local file
  for file in flake.nix home.nix; do
    if [[ ! -e "$HM_DIR/$file" ]]; then
      install -m 0644 "$HM_SEED_DIR/$file" "$HM_DIR/$file"
    fi
  done
}

nix_system() {
  case "$(uname -m)" in
    x86_64)
      printf '%s\n' x86_64-linux
      ;;
    aarch64|arm64)
      printf '%s\n' aarch64-linux
      ;;
    *)
      printf 'Unsupported architecture for a0-symbolics Home Manager: %s\n' "$(uname -m)" >&2
      return 1
      ;;
  esac
}

activate_home_manager() {
  mkdir -p \
    /nix/store \
    /nix/var/nix/profiles/per-user/root \
    /nix/var/nix/gcroots/per-user/root

  nix-store --init

  if [[ ! -e "$HM_DIR/flake.lock" ]]; then
    nix flake lock "$HM_DIR"
  fi

  local system
  system="$(nix_system)"

  nix run github:nix-community/home-manager/release-26.05 -- \
    switch \
    --flake "$HM_DIR#root-$system"
}

seed_home_manager
activate_home_manager

exec /exe/initialize.sh "${BRANCH:-local}"
