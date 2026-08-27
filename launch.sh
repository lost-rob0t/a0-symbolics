#!/usr/bin/env bash
set -euo pipefail

readonly REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly COMPOSE_DIR="$REPO_ROOT/docker/symbolics"
readonly PROJECT_NAME="${A0_SYMBOLICS_PROJECT:-a0-symbolics}"

usage() {
  printf 'Usage: %s [build|up|down] [OPTIONS]\n' "${0##*/}"
  printf '\nCommands:\n'
  printf '  build              Build the a0-symbolics image\n'
  printf '  up                 Build if needed and start in detached mode (default)\n'
  printf '  down               Stop and remove the a0-symbolics containers\n'
  printf '\nCommand options are passed through to docker compose.\n'
}

if (($# > 0)); then
  command="$1"
  shift
else
  command=up
fi

case "$command" in
  -h|--help)
    usage
    exit 0
    ;;
  build|down|up)
    ;;
  *)
    printf 'Unknown command: %s\n\n' "$command" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ ! -f "$COMPOSE_DIR/compose.yml" ]]; then
  printf 'Missing %s. Copy compose.yml.example to compose.yml first.\n' \
    "$COMPOSE_DIR/compose.yml" >&2
  exit 1
fi

cd "$COMPOSE_DIR"
compose_args=(docker compose --project-name "$PROJECT_NAME")
if [[ -f "$REPO_ROOT/.env" ]]; then
  compose_args+=(--env-file "$REPO_ROOT/.env")
fi

case "$command" in
  build)
    exec "${compose_args[@]}" build "$@"
    ;;
  down)
    exec "${compose_args[@]}" down "$@"
    ;;
  up)
    exec "${compose_args[@]}" up -d "$@"
    ;;
esac
