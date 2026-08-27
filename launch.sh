#!/usr/bin/env bash
set -euo pipefail

readonly REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly COMPOSE_DIR="$REPO_ROOT/docker/symbolics"

if [[ ! -f "$COMPOSE_DIR/compose.yml" ]]; then
  printf 'Missing %s. Copy compose.yml.example to compose.yml first.\n' \
    "$COMPOSE_DIR/compose.yml" >&2
  exit 1
fi

cd "$COMPOSE_DIR"
exec docker compose up -d "$@"
