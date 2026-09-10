# Upstream replay proof: a0-symbolics onto Agent Zero v2.12

Executed with `scripts/upstream-sync` on 2026-09-10. This is the first real
upstream replay processed by the maintenance model.

## Inputs

| Item | Value |
| --- | --- |
| Recorded base (maint/upstream.toml) | v2.10 `b22a144bf59f15b1516084c9e7b88133ba92c8a9` |
| Replay target | v2.12 `b1cbd1f960a1a5c4482b324dcff4742aa67b7a51` (verified latest stable) |
| Upstream delta | 192 commits, 508 files |
| Symbolics series | 68 non-merge commits from `v2.10..HEAD` |
| Replay branch | `a0s-replay-2-12` in isolated worktree `tmp/upstream-replay/v2.12` |

## Result

- 68/68 series commits replayed 1:1 (range-diff: 0 dropped, 0 added; textual
  `!` markers come from `-x` cherry-pick trailers and rebased context).
- 11 commits stopped on conflicts; every conflict was resolved deliberately,
  per-commit evidence in `conflicts-*.md`.
- 1 commit auto-skipped as empty (its prompt content now lives in the
  `_a0s_prompts` overlay; visible in the range-diff and final tree diff).

## Conflict resolutions (semantic record)

| Area | Resolution |
| --- | --- |
| `prompts/agent.system.main.solving.md`, persona prompts, `agent.system.tool.code_exe.md` | Follow upstream; Symbolics text now lives in `plugins/_a0s_prompts` (overlay plugin, first-class prompt path precedence). |
| `helpers/litellm_transport.py` | Merged onto upstream's rewritten transport: kept `_reported_usage` alongside the Symbolics `tool_choice`-drop retry and reasoning-effort normalization; restored the Responses-first `RESPONSES_ALIASES` default that upstream v2.12 flipped to Chat Completions. OpenRouter stays pinned to `a0_api_mode: responses` in `conf/model_providers.yaml`. |
| `helpers/extract_tools.py` | Merged cleanly: upstream's non-JSON fast-fail + tolerant DirtyJson recovery coexist with the Symbolics XML `<invoke>` parser. |
| `tests/email_parser_test.py` | Upstream deleted it; followed upstream (the fork carried a stale v2.10 copy). |
| DOX/AGENTS.md, test-file hunks | Merged both sides where contracts overlap; vendor-text assertions (`memory_load`, researcher python fence) relaxed to survive vendor rewrites. |
| `tests/test_self_update_tag_filter.py` | Kept the Symbolics `a0s-` release-tag contract (distribution-owned updates). |

Post-replay contract fix commit on the replay branch:
`946debd1 fix(tests): keep transport and prompt contracts across the v2.12 base`.

## Verification on the replayed head (`946debd1`)

`scripts/upstream-sync verify --repo tmp/upstream-replay/v2.12 --full`:

- pytest focused set: 147 passed, 0 failed (self-update policy, responses
  architecture, tool-choice retry, prompt budget/debloat, defer lifecycle,
  scheduler runs, prolog-rlm pin, auth/CSRF).
- import smoke (`agent`, `models`, `helpers.self_update`,
  `helpers.symbolics_release`): OK.
- plugin discovery (`_a0s_prompts`, `_prolog_rlm`): OK.
- Prolog runtime (`swipl`): available.
- docker compose config (`docker/symbolics/compose.yml.example`): OK.
- nix flake metadata: OK.
- Live boot: `run_ui.py` from the replay worktree started and `/api/health`
  returned 200 (branch `a0s-replay-2-12`, describe `v2.12-69-g946debd1`).
  Full image build and symbolic-mode live session remain release-pipeline
  steps and were not run from this branch.

## Fork surface (before -> after, same tool semantics)

| Metric | v2.10 base (pre-task HEAD) | v2.12 base (replayed head) |
| --- | --- | --- |
| files changed | 216 | 232 |
| files added (Symbolics-owned) | 138 | 155 |
| upstream-owned files modified | 78 | 77 |
| LOC added / removed | +11334 / -394 | +13682 / -710 |
| core-patch LOC (unavoidable + compat) | 1609 | 2493 |
| upstream-hot files touched | 7 | 8 |

The absolute numbers include the new maintenance surface itself (sync tool,
metadata, policy tests). The structural win: 6 upstream prompt files are no
longer modified by the fork (moved to `plugins/_a0s_prompts`), and the
remaining core deltas are individually documented in
`scripts/upstream-sync` (`CORE_PATCH_NOTES`). Future upstream syncs start
from this measured budget; it should shrink, not grow.

## Remaining unavoidable core patches

- `agent.py` — name-map resolution for text-extracted tool requests.
- `helpers/extract_tools.py` — XML invoke parser for text-based tool calls.
- `helpers/litellm_transport.py` + `models.py` — tool_choice drop retry and
  effort normalization (no transport extension hook exists upstream).
- `helpers/state_snapshot.py`, `helpers/defer.py` — scheduler run chaining
  and lifecycle hardening (upstreamable candidates).
- `helpers/self_update.py` + durable manager — distribution-owned update
  policy (compatibility hook; candidate for upstream-supported overlays).
- `conf/model_providers.yaml` — OpenRouter Responses-first provider policy.

## Notes

- rerere was enabled for the replay (`rerere.enabled=true`); reused
  resolutions remain reviewable through the per-commit conflict reports.
- `maint/upstream.toml` still records v2.10 as the distributed base. Bumping
  the base to the replayed v2.12 head is the upgrade-PR decision this proof
  prepares; merge it only when the replayed head is green on the release
  pipeline (image build + live symbolic smoke).
