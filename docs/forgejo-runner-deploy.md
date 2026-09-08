# Deploying a Forgejo Actions runner

Runners execute this repository's CI (`.github/workflows/`). The kit in
`scripts/forgejo-runner/` deploys a runner on any Linux host with systemd.

## Why a runner disappears from job dispatch

Two failure modes observed in production, both handled by the kit:

1. **Registration scope.** A runner registered with a *user*-level token
   never receives tasks; only repo-scoped (or org-scoped) runners are
   dispatched. `deploy.sh` registers with the repository registration
   token, so this cannot happen silently.
2. **Labels.** Jobs wait forever ("Waiting for a runner with the following
   label: ...") when no online runner advertises a matching label. Labels
   come from `config.template.yml` (CLI `--labels` are ignored by
   forgejo-runner), and `deploy.sh` verifies the "declared successfully"
   journal line before reporting success.

## Lanes

Workflows are grouped into two concurrency lanes; a runner serves a lane
through its labels:

| Lane | Workflow files | Label | Executor |
| --- | --- | --- | --- |
| `nix-ci` | `symbolics-rlm.yml`, `log-secret-masking.yml`, `context-id-security.yml` | `nix` | host (sandboxed nix, non-root build users) |
| `android-ci` | `android.yml` | `ubuntu-latest` | docker (`ghcr.io/catthehacker/ubuntu:act-latest`) |

Rules the kit encodes:

- Keep the `nix` label on **host** executors only. Docker containers cannot
  sandbox nix builds; unsandboxed root builds fail their purity checks
  (`/homeless-shelter`) and upstream package tests assume an unprivileged
  builder.
- Keep `runner.capacity` at **1** and scale horizontally. Concurrent
  SDK/nix builds on one docker runner degraded its docker daemon until
  every running job was cancelled.
- `runner.timeout` is **3h**: nix closure builds and torch-chain tests run
  long, and the Android build alone needs ~25 minutes on a quiet machine.

## Deploy

```console
TOKEN=$(curl -s -H "Authorization: token $TEA_TOKEN" \
  "https://git.starintel.actor/api/v1/repos/nsaspy/a0-symbolics/actions/runners/registration-token" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')

scripts/forgejo-runner/deploy.sh \
  --repo nsaspy/a0-symbolics \
  --token "$TOKEN" \
  --name arh-runner-2
```

The token is also available in the UI: repository *Settings → Actions →
Runners → Create new runner*. Requirements for the target host: systemd
(user units), `forgejo-runner` binary (or the known nix store path), and
for host-executor labels `nix`, `node`, `git` on the unit's PATH; for the
docker label a reachable docker daemon.

Use `--no-start` to render, register and install without enabling the
unit, and `--dir` to run several lane-dedicated runners on one machine
(trim each rendered config's label list to one lane).
