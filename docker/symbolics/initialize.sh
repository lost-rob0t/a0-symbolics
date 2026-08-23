#!/usr/bin/env bash
set -euo pipefail

readonly HM_DIR="${A0_HOME_MANAGER_DIR:-/a0/usr/home-manager}"
readonly HM_SEED_DIR="/opt/a0-symbolics/home-manager"
readonly SYSTEM_JOBS_DIR="${A0_SYSTEM_JOBS_DIR:-/a0/usr/system-jobs}"
readonly SUPERVISOR_CONF="/etc/supervisor/conf.d/supervisord.conf"

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

prepare_system_jobs() {
  local cron_bin="/root/.nix-profile/bin/cron"

  if [[ ! -x "$cron_bin" ]]; then
    printf 'Nix-managed cron binary is missing: %s\n' "$cron_bin" >&2
    return 1
  fi

  mkdir -p \
    "$SYSTEM_JOBS_DIR/cron/tabs" \
    "$SYSTEM_JOBS_DIR/scripts" \
    "$SYSTEM_JOBS_DIR/logs"
  chmod 0700 "$SYSTEM_JOBS_DIR/cron" "$SYSTEM_JOBS_DIR/cron/tabs"
  touch "$SYSTEM_JOBS_DIR/cron/cron.deny"

  # Nixpkgs' Vixie cron uses /var/cron. Keep its spool inside /a0/usr so
  # both plugin-managed jobs and manual `crontab` entries survive rebuilds.
  rm -rf /var/cron
  ln -s "$SYSTEM_JOBS_DIR/cron" /var/cron

  # Reuse Agent Zero's existing supervised cron slot, but run the Nix binary.
  sed -i \
    "s#^command=/usr/sbin/cron -f$#command=$cron_bin -n#" \
    "$SUPERVISOR_CONF"
}

seed_home_manager
activate_home_manager
prepare_system_jobs

exec /exe/initialize.sh "${BRANCH:-local}"
