"""
Real tests for orchestrator/backup_manager.py's tarball/rotation/verify
logic. The known-good CHECKS themselves (real pytest run, real py_compile,
real db read, real security scan) were exercised live via the actual CLI
during development -- three full real runs (good -> G1, deliberately
broken -> UNVERIFIED_SNAPSHOT, good again -> real rotation to G2/G3), plus
a real corruption test against an actual tarball (byte-flip -> hash
mismatch + real zlib decompression error, not a rubber-stamp check). That
full-suite-in-the-loop path is too slow/circular to run inside pytest
itself, so these tests instead cover the tarball/rotation/relabel/verify
mechanics directly, real filesystem operations against a temp root, with
_collect_checks patched to a controlled dict rather than re-running the
whole real suite recursively.
"""
import json
from pathlib import Path

import pytest

from orchestrator import backup_manager as bm


def _good_checks():
    return {
        "git": {"captured": True, "commit": "deadbeef", "branch": "main", "dirty_file_count": 0},
        "shakthi_version": "3.1.0",
        "database": {"readable": True, "integrity": "ok", "table_count": 1, "schema_hash": "abc"},
        "tests": {"passed": True, "returncode": 0, "summary": ["1 passed"]},
        "build": {"passed": True, "failures": []},
        "app_launch": {"launches": True, "route_count": "10", "detail": ""},
        "security_gate": {"clean": True, "finding_count": 0},
    }


def _bad_checks():
    checks = _good_checks()
    checks["tests"] = {"passed": False, "returncode": 1, "summary": ["1 failed"]}
    return checks


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    """A small real source tree to actually tar/hash/verify, and a
    separate real backup destination -- both real directories, not
    mocked filesystem calls."""
    source = tmp_path / "shakthi-os"
    (source / "orchestrator").mkdir(parents=True)
    (source / "orchestrator" / "real_file.py").write_text("x = 1\n")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "junk.js").write_text("should be excluded\n")

    backup_root = tmp_path / "SHAKTHI_BACKUPS" / "local"
    monkeypatch.setattr(bm, "config", type("C", (), {"ROOT": source})())
    monkeypatch.setattr(bm, "BACKUP_ROOT", backup_root)
    return source, backup_root


def test_make_tarball_excludes_node_modules_and_hashes_correctly(fake_root):
    source, backup_root = fake_root
    backup_root.mkdir(parents=True)
    dest = backup_root / "test.tar.gz"

    info = bm._make_tarball(dest)

    assert dest.exists()
    assert info["size_bytes"] == dest.stat().st_size
    assert info["sha256"] == bm._sha256_file(dest)

    import tarfile
    with tarfile.open(dest, "r:gz") as tar:
        names = tar.getnames()
    assert any("real_file.py" in n for n in names)
    assert not any("node_modules" in n for n in names)


def test_create_local_backup_known_good_promotes_to_g1(fake_root, monkeypatch):
    monkeypatch.setattr(bm, "_collect_checks", _good_checks)

    result = bm.create_local_backup("test: known good")

    assert result["status"] == "KNOWN_GOOD"
    assert result["generation"] == "G1"
    g1_meta = json.loads((bm.BACKUP_ROOT / "G1" / "metadata.json").read_text())
    assert g1_meta["generation"] == "G1"
    assert g1_meta["reason"] == "test: known good"


def test_create_local_backup_failed_checks_stores_unverified_not_g1(fake_root, monkeypatch):
    monkeypatch.setattr(bm, "_collect_checks", _bad_checks)

    result = bm.create_local_backup("test: deliberately broken")

    assert result["status"] == "UNVERIFIED_SNAPSHOT"
    assert result["generation"] is None
    assert not (bm.BACKUP_ROOT / "G1" / "metadata.json").exists()
    unverified = list((bm.BACKUP_ROOT / "unverified").glob("*.json"))
    assert len(unverified) == 1


def test_rotation_relabels_metadata_not_just_moves_files(fake_root, monkeypatch):
    """Regression test for a real bug caught live during development:
    shutil.move carries a generation dir's metadata.json content as-is,
    so without relabeling, G1's old file still says generation:'G1' after
    becoming G2 -- listing then shows 'G1' twice. This proves the fix."""
    monkeypatch.setattr(bm, "_collect_checks", _good_checks)

    bm.create_local_backup("first")
    bm.create_local_backup("second")

    g1_meta = json.loads((bm.BACKUP_ROOT / "G1" / "metadata.json").read_text())
    g2_meta = json.loads((bm.BACKUP_ROOT / "G2" / "metadata.json").read_text())
    assert g1_meta["generation"] == "G1"
    assert g2_meta["generation"] == "G2"
    assert g1_meta["reason"] == "second"
    assert g2_meta["reason"] == "first"


def test_rotation_keeps_only_three_generations(fake_root, monkeypatch):
    monkeypatch.setattr(bm, "_collect_checks", _good_checks)

    for reason in ("r1", "r2", "r3", "r4"):
        bm.create_local_backup(reason)

    result = bm.list_local_generations()
    reasons = [g["reason"] for g in result["generations"]]
    assert reasons == ["r4", "r3", "r2"]
    assert not (bm.BACKUP_ROOT / "G3" / "metadata.json").read_text().count("r1")


def test_verify_generation_detects_real_corruption(fake_root, monkeypatch):
    monkeypatch.setattr(bm, "_collect_checks", _good_checks)
    bm.create_local_backup("to be corrupted")

    good = bm.verify_generation("G1")
    assert good["verified"] is True
    assert good["hash_matches"] is True
    assert good["tar_integrity"] is True

    tarball_path = bm.BACKUP_ROOT / "G1" / "shakthi_os_backup.tar.gz"
    with open(tarball_path, "r+b") as f:
        f.seek(50)
        f.write(b"CORRUPTED")

    bad = bm.verify_generation("G1")
    assert bad["verified"] is False
    assert bad["hash_matches"] is False
    assert bad["tar_integrity"] is False


def test_verify_generation_empty_slot_reports_honestly(fake_root):
    result = bm.verify_generation("G3")
    assert result["verified"] is False
    assert "empty" in result["reason"]


def test_is_known_good_requires_every_check():
    assert bm._is_known_good(_good_checks()) is True
    assert bm._is_known_good(_bad_checks()) is False

    checks = _good_checks()
    checks["security_gate"] = {"clean": False, "finding_count": 1}
    assert bm._is_known_good(checks) is False
