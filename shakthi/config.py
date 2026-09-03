"""Runtime paths that work from any checkout location."""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    configured = os.getenv("SHAKTHI_HOME")
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[1]


def state_dir() -> Path:
    path = project_root() / "state" / "v3_1"
    path.mkdir(parents=True, exist_ok=True)
    return path

