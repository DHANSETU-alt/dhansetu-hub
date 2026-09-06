"""
Workspace path containment — the highest-risk piece of the tool system.
Every file tool call goes through resolve_in_workspace() before touching disk.
Built and reasoned about in isolation, before anything depends on it.
"""
from pathlib import Path

from .. import config


class PathEscapeError(ValueError):
    pass


def workspace_root(business_id: int) -> Path:
    root = Path(config.WORKSPACES_DIR) / f"business_{business_id}"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def resolve_in_workspace(business_id: int, relative_path: str) -> Path:
    """Resolve relative_path against the business's workspace root, refusing
    anything that could escape it.

    Order matters: reject absolute paths and null bytes BEFORE joining.
    Path("/root") / "/etc/passwd" silently discards the left side and
    evaluates to Path("/etc/passwd") — validating containment only after
    the join is too late if that gotcha isn't closed first.
    """
    if "\x00" in relative_path:
        raise PathEscapeError(f"null byte in path: {relative_path!r}")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {relative_path!r}")

    root = workspace_root(business_id)
    joined = (root / candidate).resolve()  # resolves .. segments and symlinks

    if not joined.is_relative_to(root):
        raise PathEscapeError(f"path escapes workspace: {relative_path!r}")

    return joined
