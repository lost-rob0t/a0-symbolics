#!/usr/bin/env bash
set -euo pipefail

readonly REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly COMPOSE_DIR="$REPO_ROOT/docker/symbolics"
readonly PROJECT_NAME="${A0_SYMBOLICS_PROJECT:-a0-symbolics}"

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

exec "${compose_args[@]}" up -d "$@"
