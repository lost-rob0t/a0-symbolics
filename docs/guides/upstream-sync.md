# Upstream Synchronization Guide

a0-symbolics is an upstream-replayable Agent Zero distribution, not a
conventional long-lived fork. Upstream Agent Zero is a vendored, immutable
base; everything Symbolics adds is a thin, reviewed overlay on top.

```text
agent0ai/agent-zero (immutable base commit)
    -> small reviewed core patch stack
    -> Symbolics bundled plugins/extensions (_prolog_rlm, _prolog_context_compiler, _system_jobs, _a0s_prompts, ...)
    -> packaging (Nix / Docker / Android)
    -> a0-symbolics release (a0s-v<upstream>.<series>)
```

## Canonical metadata

`maint/upstream.toml` records the immutable upstream base commit (never a
branch name) and the Symbolics distribution remotes. Only
`scripts/upstream-sync` edits it.

## Sync workflow

```bash
scripts/upstream-sync status          # base, HEAD, latest upstream
scripts/upstream-sync plan v2.13      # delta + conflict hotspots (maint/reports/plan-*.json)
scripts/upstream-sync prepare v2.13   # isolated worktree replay, stops on conflicts
# resolve conflicts in tmp/upstream-replay/<tag>, commit, then:
scripts/upstream-sync resume v2.13
scripts/upstream-sync verify --repo tmp/upstream-replay/v2.13 --full
scripts/upstream-sync promote v2.13   # move the recorded base to the replayed head
```

- `prepare` replays the Symbolics series with rerere enabled; reused conflict
  resolutions stay reviewable through the per-commit conflict reports.
- `verify` runs the focused Symbolics test set, import/plugin smoke checks,
  and (with `--full`) docker compose and nix flake checks. A live boot check
  of the replayed head is expected before merging an upgrade.
- Each conflict resolution is recorded under `maint/reports/prepare-<tag>/`;
  recurring resolutions belong in `maint/resolutions/`.
- `promote` is the only supported base transition. It validates the completed
  replay evidence (state, branch, clean worktree, upstream commit ancestry),
  rewrites `maint/upstream.toml` and the fork-surface budget on the replay
  branch, commits the promotion there, and records `promotion.json` under
  `maint/reports/prepare-<tag>/`. The replay branch then becomes the
  promotion PR; release gates run on that branch before merge.

## Self-update policy

Stable installations update from the Symbolics distribution remotes only
(`a0s-vX.Y[.Z]` release tags). Raw upstream Agent Zero is refused as an
update source and as a checkout target (the durable updater refuses any
target without the `maint/upstream.toml` marker). Development checkouts may
override with `A0_ALLOW_UPSTREAM_SELF_UPDATE=1`.

## Fork-surface budget

`scripts/upstream-sync fork-surface --write` regenerates
`maint/fork-surface.toml`. Core patches are individually classified in the
tool; the budget should shrink over time as behavior migrates into bundled
plugins and upstream accepts generalizable patches.

See `maint/reports/prepare-v2.12/REPORT.md` for the first full replay proof
and `maint/AGENTS.md` for the binding contracts.
