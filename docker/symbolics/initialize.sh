#!/usr/bin/env bash
set -euo pipefail

export USER="${USER:-root}"

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

ensure_system_jobs_home_manager() {
  local home_nix="$HM_DIR/home.nix"

  if grep -Eq '^[[:space:]]+cron[[:space:]]*$' "$home_nix"; then
    return
  fi

  python3 - "$home_nix" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
needle = "  home.packages = with pkgs; [\n"
if needle not in text:
    raise SystemExit(
        "System Jobs needs pkgs.cron, but home.packages could not be located in "
        f"{path}. Add `cron` to the Home Manager package list."
    )
path.write_text(text.replace(needle, needle + "    cron\n", 1), encoding="utf-8")
PY
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

# In-container nix builds share the compose mem_limit with the supervised
# services. Unbounded parallelism (nix defaults NIX_BUILD_CORES to every host
# core) OOM-kills the services under an 8 GiB cap, so derive a conservative
# job budget from the container's own cgroup limit. Operators override it with
# A0_NIX_MAX_JOBS / A0_NIX_CORES.
bound_nix_parallelism() {
  local jobs cores conf="/etc/nix/nix.conf"

  if [[ -n "${A0_NIX_MAX_JOBS:-}" ]]; then
    jobs="$A0_NIX_MAX_JOBS"
  else
    local limit_bytes limit_gib
    limit_bytes="$(cat /sys/fs/cgroup/memory.max 2>/dev/null || true)"
    case "$limit_bytes" in
      ''|max)
        limit_bytes=$((8 * 1024 * 1024 * 1024))
        ;;
      *)
        :
        ;;
    esac
    limit_gib=$((limit_bytes / (1024 * 1024 * 1024)))
    jobs=$((limit_gib / 4))
    (( jobs < 1 )) && jobs=1
    (( jobs > 4 )) && jobs=4
  fi

  cores="${A0_NIX_CORES:-2}"

  install -d /etc/nix
  if [[ ! -e "$conf" ]]; then
    printf '%s\n' \
      'experimental-features = nix-command flakes' \
      'sandbox = false' \
      'build-users-group =' \
      > "$conf"
  fi
  sed -i -E '/^[[:space:]]*(max-jobs|cores)[[:space:]]*=/d' "$conf"
  {
    printf '# a0-symbolics: keep in-container nix builds inside the container\n'
    printf '# memory bound; override with ~/.config/nix/nix.conf or\n'
    printf '# A0_NIX_MAX_JOBS / A0_NIX_CORES.\n'
    printf 'max-jobs = %s\n' "$jobs"
    printf 'cores = %s\n' "$cores"
  } >> "$conf"
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

activate_prolog_rlm() {
  local source_root="${A0_SOURCE_ROOT:-/git/agent-zero}"
  local prolog_rlm
  local pack_dir="${XDG_DATA_HOME:-$HOME/.local/share}/swi-prolog/pack"

  prolog_rlm="$(nix build "$source_root#prolog-rlm" --no-link --print-out-paths)"
  ln -sfn "$prolog_rlm" /nix/var/nix/gcroots/a0-symbolics-prolog-rlm
  mkdir -p "$pack_dir"
  ln -sfn "$prolog_rlm/share/swi-prolog/pack/prolog_rlm" "$pack_dir/prolog_rlm"
  export PROLOG_RLM_ROOT=""
  export SWIPL_PACK_PATH="$prolog_rlm/share/swi-prolog/pack${SWIPL_PACK_PATH:+:$SWIPL_PACK_PATH}"
}

generate_smoke_evidence() {
  (
    local smoke_tmp="/run/a0-symbolics/smoke.json.$$"
    local refresh_seconds="${A0_SMOKE_REFRESH_SECONDS:-30}"
    local ready=0

    install -d /run/a0-symbolics
    # Keep producing readiness evidence for the container lifetime. A one-shot
    # boot window permanently starves healthcheck.sh whenever the UI is slow
    # or recovering from a crash loop, leaving the container unhealthy forever.
    while true; do
      if curl --fail --silent --max-time 2 http://127.0.0.1:80/ >/dev/null; then
        if /opt/a0-symbolics/smoke.sh /a0 > "$smoke_tmp"; then
          mv "$smoke_tmp" /run/a0-symbolics/smoke.json
          ready=1
        else
          rm -f "$smoke_tmp"
        fi
        sleep "$refresh_seconds"
      elif (( ready == 0 )); then
        sleep 2
      else
        sleep "$refresh_seconds"
      fi
    done
  ) &
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
    "s#^command=/usr/sbin/cron -f\$#command=$cron_bin -n#" \
    "$SUPERVISOR_CONF"
}

seed_home_manager
ensure_system_jobs_home_manager
bound_nix_parallelism
activate_home_manager
activate_prolog_rlm
prepare_system_jobs
generate_smoke_evidence

exec /exe/initialize.sh "${BRANCH:-local}"
