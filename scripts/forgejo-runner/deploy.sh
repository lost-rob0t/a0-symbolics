#!/usr/bin/env bash
# Deploy a Forgejo Actions runner for this repository on a Linux host.
#
# Registers a REPO-scoped runner (user-scoped registrations never receive
# tasks), renders config.template.yml with an absolute state directory,
# installs a systemd --user unit, and verifies the runner declares itself.
#
# Usage:
#   ./deploy.sh --repo OWNER/NAME --token TOKEN --name NAME [--dir DIR]
#               [--instance URL] [--binary PATH] [--no-start]
#
#   --repo      Repository slug the runner serves, e.g. nsaspy/a0-symbolics.
#   --token     Repository registration token: repo Settings -> Actions ->
#               Runners -> Create new runner, or the API:
#               GET /api/v1/repos/<repo>/actions/runners/registration-token
#   --name      Runner name shown in the Forgejo UI (must be unique).
#   --dir       State directory (default: ~/.config/forgejo-runner-repo).
#   --instance  Forgejo base URL (default: https://git.starintel.actor).
#   --binary    forgejo-runner binary path (default: resolved from PATH,
#               then the known nix store path).
#   --no-start  Render, register and install, but do not enable the unit.
#
# Notes:
#   - Labels and timeouts come from config.template.yml; CLI --labels are
#     ignored by forgejo-runner (the config file is authoritative).
#   - Host-executor labels need nix, node and git on the unit's PATH.
#   - A docker-executor label needs docker reachable by the service user.
set -euo pipefail

usage() { grep '^#   ' "$0" | sed 's/^#   //'; exit 1; }

REPO="" TOKEN="" NAME="" DIR="" INSTANCE="https://git.starintel.actor" BINARY="" NO_START=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --token) TOKEN="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --dir) DIR="$2"; shift 2 ;;
    --instance) INSTANCE="$2"; shift 2 ;;
    --binary) BINARY="$2"; shift 2 ;;
    --no-start) NO_START=1; shift ;;
    -h|--help) usage ;;
    *) echo "deploy.sh: unknown argument '$1'" >&2; usage ;;
  esac
done

fail() { echo "deploy.sh: $*" >&2; exit 1; }
[[ -n "$REPO" ]] || fail "--repo is required"
[[ -n "$TOKEN" ]] || fail "--token is required"
[[ -n "$NAME" ]] || fail "--name is required"

# Resolve the runner binary before touching the system.
if [[ -z "$BINARY" ]]; then
  if command -v forgejo-runner >/dev/null 2>&1; then
    BINARY="$(command -v forgejo-runner)"
  elif [[ -x /nix/store/r0zy3bczmmv28sg6ls8zbz2g7xj48dmk-forgejo-runner-13.1.0/bin/forgejo-runner ]]; then
    BINARY=/nix/store/r0zy3bczmmv28sg6ls8zbz2g7xj48dmk-forgejo-runner-13.1.0/bin/forgejo-runner
  else
    fail "forgejo-runner not found; install it (https://forgejo.org/docs/latest/admin/actions/#forgejo-runner) or pass --binary"
  fi
fi
[[ -x "$BINARY" ]] || fail "runner binary is not executable: $BINARY"

command -v systemctl >/dev/null 2>&1 || fail "systemctl is required (systemd user units)"
TEMPLATE="$(cd "$(dirname "$0")" && pwd)/config.template.yml"
[[ -f "$TEMPLATE" ]] || fail "config template missing next to deploy.sh"

RUNNER_DIR="${DIR:-$HOME/.config/forgejo-runner-repo}"
mkdir -p "$RUNNER_DIR"
RUNNER_DIR="$(cd "$RUNNER_DIR" && pwd)"
CONFIG="$RUNNER_DIR/config.yml"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_NAME="forgejo-runner-repo.service"
mkdir -p "$UNIT_DIR"

if [[ -e "$RUNNER_DIR/.runner" ]]; then
  fail "$RUNNER_DIR/.runner already exists; pick another --dir or remove it to re-register"
fi

# Render the config: only the state-directory placeholder is substituted.
sed "s|@RUNNER_DIR@|$RUNNER_DIR|g" "$TEMPLATE" > "$CONFIG"

echo "==> registering $NAME for $REPO at $INSTANCE"
"$BINARY" register --no-interactive \
  --config "$CONFIG" \
  --instance "$INSTANCE" \
  --token "$TOKEN" \
  --name "$NAME" || fail "registration failed; check the token is the REPOSITORY registration token for $REPO"
[[ -e "$RUNNER_DIR/.runner" ]] || fail "registration did not produce $RUNNER_DIR/.runner"

# systemd --user unit. PATH must expose nix/node/git for host-executor jobs.
cat > "$UNIT_DIR/$UNIT_NAME" <<UNIT
[Unit]
Description=Forgejo Actions runner ($NAME)
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$RUNNER_DIR
ExecStart=$BINARY daemon --config $CONFIG
Environment=PATH=$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:/run/current-system/sw/bin:/usr/bin:/bin
Environment=NIX_PATH=nixpkgs=/nix/var/nix/profiles/per-user/root/channels/nixpkgs
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload

if [[ "$NO_START" -eq 1 ]]; then
  echo "==> installed $UNIT_NAME (not started); start with: systemctl --user enable --now $UNIT_NAME"
  exit 0
fi

systemctl --user enable --now "$UNIT_NAME"
sleep 5
systemctl --user is-active --quiet "$UNIT_NAME" || {
  journalctl --user -u "$UNIT_NAME" --no-pager | tail -20 >&2
  fail "unit did not become active"
}

# The runner must declare itself with its labels; without this the instance
# never dispatches jobs (it then shows jobs stuck "Waiting for a runner").
if journalctl --user -u "$UNIT_NAME" --since "-1 min" --no-pager | grep -q "declared successfully"; then
  echo "==> OK: $NAME registered, unit active, labels declared"
  echo "    verify in the UI: $INSTANCE/$REPO/settings/actions/runners"
else
  journalctl --user -u "$UNIT_NAME" --no-pager | tail -20 >&2
  fail "unit is active but never declared itself; check instance reachability"
fi
