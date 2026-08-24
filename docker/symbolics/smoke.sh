#!/usr/bin/env bash
set -euo pipefail

readonly SOURCE_ROOT="${1:-/a0}"

swipl --version >&2
swipl -q -g \
  "use_module(library(rlm)),rlm:rlm_ready,rlm:rlm_version(Version),format(user_error,'Prolog-RLM ~w ready~n',[Version]),halt"

PYTHONPATH="$SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  /opt/venv-a0/bin/python /opt/a0-symbolics/smoke.py "$SOURCE_ROOT"
