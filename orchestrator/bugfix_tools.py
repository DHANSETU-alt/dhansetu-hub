"""
Path handling for the Bug Fixer's two distinct access levels -- this is
deliberately NOT the same module as orchestrator/tools/paths.py, because
the two have different threat models:

  - orchestrator/tools/paths.py scopes an agent to ONE business's workspace
    -- a customer-data sandbox, isolating tenants from each other.
  - This module scopes the Bug Fixer to the PLATFORM'S OWN SOURCE CODE --
    there is no tenant isolation question, but there is a much bigger one:
    an agent that can silently rewrite the orchestrator it runs inside of
    is a fundamentally different risk than one that writes a customer's
    website file.

The rule enforced here: READ access to the real codebase (codebase_root),
WRITE access ONLY to a staging area (.bugfixes/<bug_id>/) that is never on
the live import path. Moving a staged patch onto a real source file is a
separate, explicit, human-confirmed operation in bug_fixer.apply_patch() --
never something a tool call can do by itself, and never something the
agent's model output can trigger directly.
"""
from pathlib import Path

from . import config
from .tools.paths import PathEscapeError

STAGING_DIR = config.ROOT / ".bugfixes"


def codebase_root() -> Path:
    return config.ROOT.resolve()


def resolve_in_codebase(relative_path: str) -> Path:
    """Read-only resolution against the real project root. Same containment
    rules as tools/paths.py (reject absolute/null-byte before joining,
    resolve, verify containment) -- duplicated rather than imported because
    the root differs and a copy-paste-and-forget divergence here would be
    a real security bug, not a style nit. Kept deliberately tiny so the two
    can be eyeballed side by side."""
    if "\x00" in relative_path:
        raise PathEscapeError(f"null byte in path: {relative_path!r}")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {relative_path!r}")

    root = codebase_root()
    joined = (root / candidate).resolve()
    if not joined.is_relative_to(root):
        raise PathEscapeError(f"path escapes codebase root: {relative_path!r}")
    # Never let the "read the codebase" tool read its own staged patches,
    # the live DB file, or anything gitignored/secret-shaped -- those are
    # either not "code" in the sense a bug report cares about, or are
    # exactly the kind of file a patch-reviewer should not be echoing back.
    denylist = (".env", ".git", "shakthi.db", "node_modules", ".bugfixes", "workspaces")
    if any(part in denylist for part in joined.relative_to(root).parts):
        raise PathEscapeError(f"refusing to read a denylisted path: {relative_path!r}")
    return joined


def staging_dir_for(bug_id: int) -> Path:
    d = STAGING_DIR / str(bug_id)
    d.mkdir(parents=True, exist_ok=True)
    # .resolve() matters here, not just tidiness: on macOS /tmp and /var are
    # themselves symlinks (-> /private/tmp, /private/var). Without this, an
    # unresolved root compared against a resolved `joined` path in
    # resolve_in_staging() below false-positives as "escaped" for every
    # legitimate path under a tempdir-based STAGING_DIR -- caught by
    # tests/test_bug_fixer.py, not by inspection.
    return d.resolve()


def resolve_in_staging(bug_id: int, relative_path: str) -> Path:
    """Write access lives here ONLY -- this is a plain subdirectory of
    .bugfixes/, never anywhere near the real source tree."""
    if "\x00" in relative_path:
        raise PathEscapeError(f"null byte in path: {relative_path!r}")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {relative_path!r}")

    root = staging_dir_for(bug_id)
    joined = (root / candidate).resolve()
    if not joined.is_relative_to(root):
        raise PathEscapeError(f"path escapes staging dir: {relative_path!r}")
    return joined


def read_source_file(relative_path: str) -> str:
    path = resolve_in_codebase(relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"no such file in codebase: {relative_path!r}")
    return path.read_text(errors="replace")


def write_staged_patch(bug_id: int, relative_path: str, content: str) -> Path:
    path = resolve_in_staging(bug_id, relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
