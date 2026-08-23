"""
Covers the deterministic, offline-testable parts of the Bug Fixer:
codebase/staging path containment, the dangerous-pattern/secret scan a
proposed patch goes through, and JSON-block parsing. Does NOT exercise the
model-calling pipeline stages (analyze/propose/qa/security/ceo review) --
those need a live local model and are exercised manually, the same way
routing.py's loop was proven in earlier phases.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import bug_fixer, bugfix_tools as bft, config
from orchestrator.tools.paths import PathEscapeError


class TestBugfixToolsContainment(unittest.TestCase):
    def setUp(self):
        self._orig_staging = bft.STAGING_DIR
        self._tmp = tempfile.mkdtemp(prefix="shakthi_bugtest_")
        bft.STAGING_DIR = Path(self._tmp) / ".bugfixes"

    def tearDown(self):
        bft.STAGING_DIR = self._orig_staging
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_read_real_source_file(self):
        content = bft.read_source_file("orchestrator/config.py")
        self.assertIn("WORKSPACES_DIR", content)

    def test_codebase_traversal_blocked(self):
        with self.assertRaises(PathEscapeError):
            bft.resolve_in_codebase("../../etc/passwd")

    def test_codebase_absolute_path_blocked(self):
        with self.assertRaises(PathEscapeError):
            bft.resolve_in_codebase("/etc/passwd")

    def test_codebase_denylist_blocks_db_and_git(self):
        with self.assertRaises(PathEscapeError):
            bft.resolve_in_codebase("shakthi.db")
        with self.assertRaises(PathEscapeError):
            bft.resolve_in_codebase(".git/config")

    def test_staging_write_is_contained(self):
        path = bft.write_staged_patch(42, "fix.py", "print('patched')")
        self.assertTrue(str(path).endswith(".bugfixes/42/fix.py"))
        self.assertEqual(path.read_text(), "print('patched')")

    def test_staging_traversal_blocked(self):
        with self.assertRaises(PathEscapeError):
            bft.resolve_in_staging(42, "../../../orchestrator/config.py")


class TestPatchSecurityScan(unittest.TestCase):
    def test_eval_flagged(self):
        matches = [name for name, p in bug_fixer.DANGEROUS_PATCH_PATTERNS.items() if p.search("result = eval(user_input)")]
        self.assertIn("eval_call", matches)

    def test_shell_true_flagged(self):
        matches = [name for name, p in bug_fixer.DANGEROUS_PATCH_PATTERNS.items()
                   if p.search("subprocess.run(cmd, shell=True)")]
        self.assertIn("shell_true", matches)

    def test_clean_code_not_flagged(self):
        clean = "def add(a, b):\n    return a + b\n"
        matches = [name for name, p in bug_fixer.DANGEROUS_PATCH_PATTERNS.items() if p.search(clean)]
        self.assertEqual(matches, [])

    def test_sensitive_file_detection(self):
        self.assertTrue(any(s in "orchestrator/tools/paths.py" for s in bug_fixer.SENSITIVE_FILES))
        self.assertFalse(any(s in "orchestrator/finance.py" for s in bug_fixer.SENSITIVE_FILES))


class TestJsonBlockParsing(unittest.TestCase):
    def test_parses_valid_block(self):
        text = 'Some reasoning.\n```json\n{"severity": "high", "confidence": 80}\n```'
        parsed = bug_fixer._parse_json_block(text)
        self.assertEqual(parsed, {"severity": "high", "confidence": 80})

    def test_returns_none_on_malformed(self):
        text = "```json\n{not valid json}\n```"
        self.assertIsNone(bug_fixer._parse_json_block(text))

    def test_returns_none_with_no_block(self):
        self.assertIsNone(bug_fixer._parse_json_block("just plain text, no fence"))


if __name__ == "__main__":
    unittest.main()
