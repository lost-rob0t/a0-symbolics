from __future__ import annotations

import os
import re
import subprocess
import tomllib
from functools import lru_cache
from pathlib import Path


MAINTENANCE_METADATA = Path(__file__).resolve().parents[1] / "maint" / "upstream.toml"
UPSTREAM_REPO_SIGNATURES = ("agent0ai/agent-zero",)
DEFAULT_RELEASE_PREFIX = "a0s-"


@lru_cache(maxsize=8)
def load_maintenance_metadata(path: str | None = None) -> dict:
    """Load maint/upstream.toml; returns {} when the file is missing."""
    target = Path(path) if path else MAINTENANCE_METADATA
    if not target.exists():
        return {}
    with target.open("rb") as handle:
        data = tomllib.load(handle)
    return data if isinstance(data, dict) else {}


def get_release_prefix(metadata: dict | None = None) -> str:
    data = metadata if metadata is not None else load_maintenance_metadata()
    prefix = str(data.get("distribution", {}).get("release_prefix", "")).strip()
    return prefix or DEFAULT_RELEASE_PREFIX


def get_distribution_repo_urls(metadata: dict | None = None) -> list[str]:
    data = metadata if metadata is not None else load_maintenance_metadata()
    distribution = data.get("distribution", {})
    urls: list[str] = []
    for key in ("repository", "repository_mirror"):
        value = str(distribution.get(key, "")).strip()
        if value and value not in urls:
            urls.append(value)
    return urls


def get_upstream_info(metadata: dict | None = None) -> dict[str, str]:
    data = metadata if metadata is not None else load_maintenance_metadata()
    upstream = data.get("upstream", {})
    return {
        "repository": str(upstream.get("repository", "")),
        "tag": str(upstream.get("tag", "")),
        "commit": str(upstream.get("commit", "")),
    }


def is_upstream_repo_url(url: str) -> bool:
    normalized = str(url or "").strip().lower()
    return any(signature in normalized for signature in UPSTREAM_REPO_SIGNATURES)


def parse_release_tag(tag: str, metadata: dict | None = None) -> tuple[int, int, int] | None:
    """Parse a distribution release tag like a0s-v2.10.1 into (major, minor, series)."""
    prefix = get_release_prefix(metadata)
    match = re.fullmatch(
        rf"{re.escape(prefix)}v(\d+)\.(\d+)(?:\.(\d+))?",
        str(tag or "").strip(),
    )
    if not match:
        return None
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3) or 0),
    )


def format_release_tag(major: int, minor: int, series: int, metadata: dict | None = None) -> str:
    prefix = get_release_prefix(metadata)
    return f"{prefix}v{major}.{minor}.{series}"


def get_symbolics_version(metadata: dict | None = None) -> str:
    data = metadata if metadata is not None else load_maintenance_metadata()
    tag = get_upstream_info(data).get("tag", "")
    if not tag:
        return ""
    series = int(data.get("distribution", {}).get("series", 0))
    return f"{get_release_prefix(data)}{tag}.{series}"


def get_symbolics_release_identity(repo_dir: str | None = None) -> dict[str, str]:
    """Release identity tying the Symbolics distribution to its upstream base."""
    metadata = load_maintenance_metadata()
    repository = str(repo_dir or MAINTENANCE_METADATA.parents[1])
    symbolics_commit = ""
    try:
        completed = subprocess.run(
            ["git", "-C", repository, "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        symbolics_commit = completed.stdout.strip()
    except Exception:
        symbolics_commit = ""
    return {
        "symbolics_version": get_symbolics_version(metadata),
        "upstream_tag": get_upstream_info(metadata).get("tag", ""),
        "upstream_commit": get_upstream_info(metadata).get("commit", ""),
        "symbolics_commit": symbolics_commit,
    }