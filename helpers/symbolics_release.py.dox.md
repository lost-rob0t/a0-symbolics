# symbolics_release.py DOX

## Purpose

- Own the a0-symbolics distribution identity: canonical upstream base metadata
  and the `a0s-vX.Y[.Z]` release identity derived from it.

## Ownership

- `symbolics_release.py` owns maintenance metadata loading and release
  identity formatting.
- `symbolics_release.py.dox.md` owns durable notes about responsibilities,
  contracts, side effects, and verification for that implementation.
- Top-level functions:
  - `load_maintenance_metadata(path: str | None=...) -> dict`
  - `get_release_prefix(metadata: dict | None=...) -> str`
  - `get_distribution_repo_urls(metadata: dict | None=...) -> list[str]`
  - `get_upstream_info(metadata: dict | None=...) -> dict[str, str]`
  - `is_upstream_repo_url(url: str) -> bool`
  - `parse_release_tag(tag: str, metadata: dict | None=...) -> tuple[int, int, int] | None`
  - `format_release_tag(major: int, minor: int, series: int, metadata: dict | None=...) -> str`
  - `get_symbolics_version(metadata: dict | None=...) -> str`
  - `get_symbolics_release_identity(repo_dir: str | None=...) -> dict[str, str]`
- Notable constants/configuration names: `MAINTENANCE_METADATA`, `UPSTREAM_REPO_SIGNATURES`, `DEFAULT_RELEASE_PREFIX`.

## Runtime Contracts

- `maint/upstream.toml` is the single source of truth for the immutable
  upstream base (`[upstream]` repository/tag/commit) and the distribution
  remotes (`[distribution]`).
- `load_maintenance_metadata` is cached and returns `{}` when the metadata
  file is absent; callers must treat that as "no distribution configured".
- `get_symbolics_release_identity` shells out to `git rev-parse HEAD` for the
  Symbolics commit and never raises on failure (returns an empty commit).
- No network access and no settings persistence happen here.

## Key Concepts

- The upstream commit is immutable and authoritative; never identify the base
  by a mutable branch name.
- Release identity semantics: `a0s-<upstream-tag>.<series>` where the upstream
  tag names the Agent Zero family and the series digit is the Symbolics
  distribution revision on that base.

## Work Guidance

- Update `maint/upstream.toml` only through `scripts/upstream-sync`.
- Keep this module dependency-light; it is imported by the self-update policy
  and maintenance tooling.

## Verification

- Run `pytest tests/test_self_update_policy.py` and
  `pytest tests/test_upstream_sync.py`.

## Child DOX Index

No child DOX files.