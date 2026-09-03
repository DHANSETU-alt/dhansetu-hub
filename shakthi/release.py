"""Single source of truth for release identity."""

from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from . import __version__
from .config import project_root


@dataclass(frozen=True)
class ReleaseIdentity:
    product: str
    version: str
    edition: str
    environment: str
    channel: str
    build: str
    git_commit: str


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=project_root(), capture_output=True,
            text=True, timeout=2, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE"


def release_identity() -> dict[str, str]:
    stamp = os.getenv("SHAKTHI_BUILD") or datetime.fromtimestamp(
        (project_root() / "shakthi" / "__init__.py").stat().st_mtime, timezone.utc
    ).strftime("%Y%m%d.%H%M")
    return asdict(ReleaseIdentity(
        product="SHAKTHI_OS", version=__version__, edition="Ultra Omni Intelligence",
        environment=os.getenv("SHAKTHI_ENV", "development").upper(),
        channel=os.getenv("SHAKTHI_RELEASE_CHANNEL", "local").upper(), build=stamp,
        git_commit=_git_commit(),
    ))

