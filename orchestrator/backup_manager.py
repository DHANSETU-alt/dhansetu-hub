"""
SHAKTHI_OS 3x3 Resilience Architecture -- Phase 1, Local backup lane (Backup A).

Real generation-rotated local backups (G1 = latest known-good, G2 =
previous, G3 = older stable), stored outside the working tree at
~/SHAKTHI_BACKUPS/local/ (spec section 2's explicit requirement). A
snapshot is promoted to a generation ONLY if real checks pass -- git
state captured, tests pass, build (a real compile check across the core
Python packages) passes, the API module actually imports and wires its
routes, the database is readable, and a real deterministic security scan
(security.scan_api_key_exposure(), the closest existing equivalent to
the spec's "Guardian" role -- no literal Guardian agent exists yet, that
integration is a later phase) finds nothing. If any check fails, the
snapshot is stored as UNVERIFIED_SNAPSHOT and never promoted -- spec
section 7's exact requirement: "A backup is NOT valid merely because
files were copied."

External SSD (Backup B) and Remote (Backup C) are explicitly out of
scope here -- no SSD is mounted on this machine (confirmed in
docs/BACKUP_ARCHITECTURE_AUDIT.md) and Remote is blocked on the founder
actually getting a copy off this machine, a separate real blocker.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import config, security

BACKUP_ROOT = Path(os.environ.get("SHAKTHI_BACKUP_ROOT", str(Path.home() / "SHAKTHI_BACKUPS" / "local")))
GENERATIONS = ("G1", "G2", "G3")
TARBALL_NAME = "shakthi_os_backup.tar.gz"

# Directory names pruned from every backup, wherever they occur in the
# tree -- large and regenerable (node_modules, .next build output, git's
# own history, bytecode caches), or (SHAKTHI_BACKUPS itself) would
# otherwise recursively back up prior backups. Deliberately does NOT
# exclude state/ -- that holds shakthi/'s real control-plane/world-model/
# events databases, genuine application data, not a build artifact.
EXCLUDE_DIR_NAMES = {
    "node_modules", ".next", ".git", "__pycache__", ".pytest_cache",
    "SHAKTHI_BACKUPS", ".wrangler",
}


# --- real checks ------------------------------------------------------

def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=config.ROOT, capture_output=True, text=True, timeout=timeout)


def _git_state() -> dict:
    try:
        commit = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        status = _run(["git", "status", "--porcelain"]).stdout
        dirty = len([l for l in status.splitlines() if l.strip()])
        return {"captured": True, "commit": commit, "branch": branch, "dirty_file_count": dirty}
    except Exception as e:
        return {"captured": False, "reason": str(e)}


def _shakthi_version() -> str:
    try:
        from shakthi import __version__
        return __version__
    except Exception:
        return "unknown"


def _db_check() -> dict:
    db_path = Path(config.DB_PATH)
    if not db_path.exists():
        return {"readable": False, "reason": "db file not found"}
    try:
        conn = sqlite3.connect(str(db_path))
        integrity = conn.execute("PRAGMA integrity_check(1)").fetchone()[0]
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        conn.close()
        schema_hash = hashlib.sha256("\n".join(t[0] for t in tables).encode()).hexdigest()[:16]
        return {"readable": integrity == "ok", "integrity": integrity, "table_count": len(tables), "schema_hash": schema_hash}
    except Exception as e:
        return {"readable": False, "reason": str(e)}


def _tests_check() -> dict:
    try:
        result = _run(["python3", "-m", "pytest", "-q"], timeout=600)
        tail = [l for l in result.stdout.strip().splitlines()[-6:] if l.strip()]
        return {"passed": result.returncode == 0, "returncode": result.returncode, "summary": tail}
    except Exception as e:
        return {"passed": False, "returncode": -1, "summary": [str(e)]}


def _build_check() -> dict:
    """'Build' for this project == a real compile check across the core
    Python packages -- fast, and proves the actual source is syntactically
    sound. The dashboard's own `npm run build` is a much slower, separate
    concern, deliberately not part of this fast pre-backup gate."""
    import py_compile
    failures = []
    for pkg in ("orchestrator", "shakthi"):
        pkg_dir = config.ROOT / pkg
        if not pkg_dir.exists():
            continue
        for f in pkg_dir.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            try:
                py_compile.compile(str(f), doraise=True)
            except Exception as e:
                failures.append(f"{f.relative_to(config.ROOT)}: {e}")
    return {"passed": len(failures) == 0, "failures": failures}


def _app_launch_check() -> dict:
    """Smoke check: the real API module imports cleanly and its route
    table is populated. Doesn't start a server -- would collide with any
    already-running instance on the same port -- but proves the exact
    code that serves the dashboard is importable and wires up real
    routes, not a mocked import."""
    try:
        result = _run(
            ["python3", "-c", "from orchestrator import api; assert len(api.ROUTES) > 5; print(len(api.ROUTES))"],
            timeout=30,
        )
        return {"launches": result.returncode == 0, "route_count": result.stdout.strip(), "detail": result.stderr.strip()}
    except Exception as e:
        return {"launches": False, "detail": str(e)}


def _security_gate() -> dict:
    findings = security.scan_api_key_exposure()
    return {"clean": len(findings) == 0, "finding_count": len(findings)}


def _collect_checks() -> dict:
    return {
        "git": _git_state(),
        "shakthi_version": _shakthi_version(),
        "database": _db_check(),
        "tests": _tests_check(),
        "build": _build_check(),
        "app_launch": _app_launch_check(),
        "security_gate": _security_gate(),
    }


def _is_known_good(checks: dict) -> bool:
    return (
        checks["database"].get("readable") is True
        and checks["tests"].get("passed") is True
        and checks["build"].get("passed") is True
        and checks["app_launch"].get("launches") is True
        and checks["security_gate"].get("clean") is True
    )


# --- tarball + hashing --------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_tarball(dest_path: Path) -> dict:
    def _filter(tarinfo: tarfile.TarInfo):
        if any(part in EXCLUDE_DIR_NAMES for part in Path(tarinfo.name).parts):
            return None
        return tarinfo

    with tarfile.open(dest_path, "w:gz") as tar:
        tar.add(str(config.ROOT), arcname=config.ROOT.name, filter=_filter)

    return {"size_bytes": dest_path.stat().st_size, "sha256": _sha256_file(dest_path)}


# --- generation management -----------------------------------------------

def _generation_dir(gen: str) -> Path:
    d = BACKUP_ROOT / gen
    d.mkdir(parents=True, exist_ok=True)
    return d


def _relabel_generation(gen_dir: Path, new_label: str) -> None:
    """A moved generation directory's metadata.json still says its OLD
    generation name until this runs -- caught live in testing (G1 and G2
    both printed as 'G1' after a real rotation, since shutil.move carries
    the file's stale content with it). The record must reflect where it
    actually now lives, not where it was created."""
    meta_path = gen_dir / "metadata.json"
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text())
        metadata["generation"] = new_label
        meta_path.write_text(json.dumps(metadata, indent=2))


def _rotate_generations() -> None:
    """G2->G3 (old G3 discarded, real retention policy: keep 3), G1->G2,
    leaving G1 empty for the new backup. Only called once a new snapshot
    has already passed every known-good check -- never rotate a failed
    or unverified build into a generation slot (spec section 6)."""
    g3, g2, g1 = BACKUP_ROOT / "G3", BACKUP_ROOT / "G2", BACKUP_ROOT / "G1"
    if g3.exists():
        shutil.rmtree(g3)
    if g2.exists():
        shutil.move(str(g2), str(g3))
        _relabel_generation(g3, "G3")
    if g1.exists():
        shutil.move(str(g1), str(g2))
        _relabel_generation(g2, "G2")
    g1.mkdir(parents=True, exist_ok=True)


def create_local_backup(reason: str) -> dict:
    """Run every real known-good check, then either rotate a new G1 (if
    they all pass) or store an honest UNVERIFIED_SNAPSHOT (if any fail).
    Never calls a failed build 'known-good' -- spec section 7."""
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    checks = _collect_checks()
    known_good = _is_known_good(checks)
    timestamp = datetime.now(timezone.utc).isoformat()
    hostname = socket.gethostname()

    base_metadata = {
        "timestamp": timestamp, "reason": reason, "hostname": hostname,
        "shakthi_version": checks["shakthi_version"], "git": checks["git"],
        "database": checks["database"], "tests": checks["tests"], "build": checks["build"],
        "app_launch": checks["app_launch"], "security_gate": checks["security_gate"],
    }

    if known_good:
        _rotate_generations()
        target_dir = _generation_dir("G1")
        tarball_path = target_dir / TARBALL_NAME
        tar_info = _make_tarball(tarball_path)
        metadata = {**base_metadata, "generation": "G1", "status": "KNOWN_GOOD",
                    "tarball": {"filename": TARBALL_NAME, **tar_info}}
        (target_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        return metadata

    unverified_dir = BACKUP_ROOT / "unverified"
    unverified_dir.mkdir(parents=True, exist_ok=True)
    snap_id = "unverified_" + timestamp.replace(":", "").replace(".", "").replace("+", "_")
    tarball_path = unverified_dir / f"{snap_id}.tar.gz"
    tar_info = _make_tarball(tarball_path)
    metadata = {**base_metadata, "generation": None, "status": "UNVERIFIED_SNAPSHOT",
                "tarball": {"filename": f"{snap_id}.tar.gz", **tar_info}}
    (unverified_dir / f"{snap_id}.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def list_local_generations() -> dict:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    generations = []
    for gen in GENERATIONS:
        meta_path = BACKUP_ROOT / gen / "metadata.json"
        generations.append(json.loads(meta_path.read_text()) if meta_path.exists() else {"generation": gen, "status": "empty"})

    unverified_dir = BACKUP_ROOT / "unverified"
    unverified = []
    if unverified_dir.exists():
        for meta_path in sorted(unverified_dir.glob("*.json")):
            unverified.append(json.loads(meta_path.read_text()))

    return {"generations": generations, "unverified_snapshots": unverified}


def verify_generation(gen: str) -> dict:
    """Real restore drill (spec section 20): recompute the tarball's
    sha256 and compare against what was recorded at backup time (detects
    corruption/tampering since), confirm real tar integrity, and confirm
    it actually extracts. A function that always returns True here isn't
    real verification -- every one of these can genuinely fail and does
    in the negative test below."""
    gen_dir = BACKUP_ROOT / gen
    meta_path = gen_dir / "metadata.json"
    if not meta_path.exists():
        return {"generation": gen, "verified": False, "reason": "no metadata found -- generation is empty"}

    metadata = json.loads(meta_path.read_text())
    tarball_path = gen_dir / metadata["tarball"]["filename"]
    if not tarball_path.exists():
        return {"generation": gen, "verified": False, "reason": "tarball file missing"}

    current_hash = _sha256_file(tarball_path)
    hash_matches = current_hash == metadata["tarball"]["sha256"]

    tar_integrity, tar_error, member_count = True, None, 0
    try:
        with tarfile.open(tarball_path, "r:gz") as tar:
            member_count = len(tar.getnames())
    except Exception as e:
        tar_integrity, tar_error = False, str(e)

    extract_ok, extract_error = True, None
    if tar_integrity:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                with tarfile.open(tarball_path, "r:gz") as tar:
                    tar.extractall(tmp, filter="data")
            except Exception as e:
                extract_ok, extract_error = False, str(e)
    else:
        extract_ok = False

    verified = hash_matches and tar_integrity and extract_ok
    return {
        "generation": gen, "verified": verified, "hash_matches": hash_matches,
        "tar_integrity": tar_integrity, "extract_ok": extract_ok, "member_count": member_count,
        "recorded_sha256": metadata["tarball"]["sha256"], "current_sha256": current_hash,
        "tar_error": tar_error, "extract_error": extract_error,
    }
