#!/usr/bin/env bash
set -euo pipefail

test -s /run/a0-symbolics/smoke.json
command -v swipl >/dev/null
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:80/ >/dev/null
supervisorctl status | awk '
  NF && $2 != "RUNNING" { exit 1 }
  END { if (NR == 0) exit 1 }
'
