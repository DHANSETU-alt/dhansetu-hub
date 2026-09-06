"""Regression test for a real recurring false positive: check_security()
used to scan tests/ alongside orchestrator/, flagging the dummy
eval()/shell=True strings inside test_bug_fixer.py's own detector tests
as if they were live dangerous code. Closed real bug tracker ids 1, 2, 3
against this exact issue before the fix landed.
"""
from pathlib import Path

from orchestrator import audit


def test_check_security_ignores_tests_directory():
    sources = {
        Path("/repo/tests/test_bug_fixer.py"): "result = eval(user_input)\n",
        Path("/repo/tests/test_other.py"): "subprocess.run(cmd, shell=True)\n",
    }
    import orchestrator.bugfix_tools as bft
    orig = bft.codebase_root
    bft.codebase_root = lambda: Path("/repo")
    try:
        findings = audit.check_security(sources)
    finally:
        bft.codebase_root = orig
    assert findings == []


def test_check_security_still_flags_real_orchestrator_code():
    sources = {Path("/repo/orchestrator/somewhere.py"): "result = eval(user_input)\n"}
    import orchestrator.bugfix_tools as bft
    orig = bft.codebase_root
    bft.codebase_root = lambda: Path("/repo")
    try:
        findings = audit.check_security(sources)
    finally:
        bft.codebase_root = orig
    assert len(findings) == 1
    assert findings[0]["description"] == "Dangerous pattern: eval_call"
