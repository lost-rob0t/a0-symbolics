#!/usr/bin/env bash
set -euo pipefail

export USER="${USER:-root}"

readonly HM_DIR="${A0_HOME_MANAGER_DIR:-/a0/usr/home-manager}"
readonly HM_SEED_DIR="/opt/a0-symbolics/home-manager"
readonly SYSTEM_JOBS_DIR="${A0_SYSTEM_JOBS_DIR:-/a0/usr/system-jobs}"
readonly SUPERVISOR_CONF="/etc/supervisor/conf.d/supervisord.conf"
readonly PERSISTENT_HOME_DIR="${A0_PERSISTENT_HOME_DIR:-/a0/usr/home}"

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
    local attempt
    local smoke_tmp="/run/a0-symbolics/smoke.json.$$"

    install -d /run/a0-symbolics
    for attempt in $(seq 1 180); do
      if curl --fail --silent --max-time 2 http://127.0.0.1:80/ >/dev/null; then
        if /opt/a0-symbolics/smoke.sh /a0 > "$smoke_tmp"; then
          mv "$smoke_tmp" /run/a0-symbolics/smoke.json
        else
          rm -f "$smoke_tmp"
        fi
        return
      fi
      sleep 2
    done
    printf 'Agent Zero did not become ready for the symbolic smoke test.\n' >&2
  ) &
}

restore_home() {
  local src="$PERSISTENT_HOME_DIR"
  local dst="${A0_HOME_DIR:-/root}"

  if [[ ! -d "$src" ]]; then
    mkdir -p "$src"
    printf 'Persistent home %s is empty; using a fresh %s.\n' "$src" "$dst"
    return
  fi

  if [[ "$src" -ef "$dst" ]]; then
    return
  fi

  mkdir -p "$dst"

  local entry
  local target
  for entry in "$src"/* "$src"/.[!.]* "$src"/..?*; do
    [[ -e "$entry" ]] || continue
    target="$dst/$(basename "$entry")"
    if [[ -e "$target" && ! -L "$target" ]]; then
      # Replace only empty real directories (like a bare image-created .ssh);
      # non-empty image- or Home-Manager-owned entries always win.
      if [[ -d "$target" ]] && [[ -z "$(ls -A "$target" 2>/dev/null)" ]]; then
        rm -rf -- "$target"
      else
        printf 'Keeping existing %s over persistent home entry %s.\n' "$target" "$entry"
        continue
      fi
    fi
    rm -rf -- "$target"
    ln -s -- "$entry" "$target"
  done
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
activate_home_manager
activate_prolog_rlm
restore_home
prepare_system_jobs
generate_smoke_evidence

exec /exe/initialize.sh "${BRANCH:-local}"
