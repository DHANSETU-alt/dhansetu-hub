"""
Stdlib unittest, no new dependency. Run with: python3 -m unittest discover tests
Covers exactly the guarantees Phase 0.2 exists to make: path containment,
permission enforcement + audit logging, and the dangerous-tier gate.

Runs against an isolated temp DB and temp workspace root -- NOT shakthi.db.
An earlier version of this file used the real DB directly, which left test
businesses/tasks sitting in the actual dashboard after every test run. That
was a real bug, not a style choice: a test suite must never write into
production data as a side effect of running.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import config, db, registry
from orchestrator.tools import dispatch, exec_tools, paths


class IsolatedDBTestCase(unittest.TestCase):
    """Points config.DB_PATH and config.WORKSPACES_DIR at a fresh temp dir
    for the duration of each test, and restores the real paths after."""

    def setUp(self):
        self._orig_db_path = config.DB_PATH
        self._orig_workspaces_dir = config.WORKSPACES_DIR
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_test_")
        config.DB_PATH = os.path.join(self._tmp_dir, "test.db")
        config.WORKSPACES_DIR = Path(self._tmp_dir) / "workspaces"
        db.init_db()
        registry.sync_registry()  # real agents/*.yaml -> temp DB, so FK-referencing tests work

    def tearDown(self):
        config.DB_PATH = self._orig_db_path
        config.WORKSPACES_DIR = self._orig_workspaces_dir
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestPathContainment(IsolatedDBTestCase):
    def test_normal_path_resolves_inside_workspace(self):
        p = paths.resolve_in_workspace(999, "a/b.txt")
        self.assertTrue(str(p).endswith("workspaces/business_999/a/b.txt"))

    def test_dotdot_traversal_blocked(self):
        with self.assertRaises(paths.PathEscapeError):
            paths.resolve_in_workspace(999, "../../etc/passwd")

    def test_absolute_path_blocked(self):
        # the pathlib join gotcha: Path("/root") / "/etc/passwd" == Path("/etc/passwd")
        with self.assertRaises(paths.PathEscapeError):
            paths.resolve_in_workspace(999, "/etc/passwd")

    def test_null_byte_blocked(self):
        with self.assertRaises(paths.PathEscapeError):
            paths.resolve_in_workspace(999, "foo\x00bar")

    def test_symlink_escape_blocked(self):
        root = paths.workspace_root(999)
        outside = Path(tempfile.mkdtemp(prefix="shakthi_test_outside_"))
        link = root / "escape_link"
        if link.exists() or link.is_symlink():
            link.unlink()
        os.symlink(outside, link)
        try:
            with self.assertRaises(paths.PathEscapeError):
                paths.resolve_in_workspace(999, "escape_link/x.txt")
        finally:
            link.unlink()


class TestDispatchPermissions(IsolatedDBTestCase):
    def setUp(self):
        super().setUp()
        with db.get_conn() as conn:
            self.business_id = db.insert_business(conn, "Test Business (test_tools.py)")
            self.task_id = db.insert_task(conn, "qa", "test", self.business_id, "normal")

    def test_denied_call_is_audited(self):
        with db.get_conn() as conn:
            agent = {"id": "no_tools_agent", "allowed_tools": "[]"}
            result = dispatch.execute_tool(conn, self.task_id, agent, self.business_id, "write_file", {"path": "x.txt", "content": "x"})
            self.assertTrue(result["denied"])
            calls = db.recent_tool_calls(conn, limit=1)
            self.assertEqual(calls[0]["decision"], "denied")
            self.assertEqual(calls[0]["tool_name"], "write_file")

    def test_allowed_call_executes_and_is_audited(self):
        with db.get_conn() as conn:
            agent = {"id": "file_agent", "allowed_tools": '["write_file"]'}
            result = dispatch.execute_tool(conn, self.task_id, agent, self.business_id, "write_file", {"path": "ok.txt", "content": "ok"})
            self.assertTrue(result["ok"])
            calls = db.recent_tool_calls(conn, limit=1)
            self.assertEqual(calls[0]["decision"], "allowed")

    def test_dangerous_tool_denied_without_global_gate(self):
        config.ALLOW_EXEC = False
        with db.get_conn() as conn:
            agent = {"id": "exec_agent", "allowed_tools": '["run_command"]'}
            result = dispatch.execute_tool(conn, self.task_id, agent, self.business_id, "run_command", {"argv": ["python3", "-c", "print(1)"]})
            self.assertTrue(result["denied"])

    def test_dangerous_tool_allowed_with_global_gate(self):
        config.ALLOW_EXEC = True
        try:
            with db.get_conn() as conn:
                agent = {"id": "exec_agent", "allowed_tools": '["run_command"]'}
                result = dispatch.execute_tool(conn, self.task_id, agent, self.business_id, "run_command", {"argv": ["python3", "-c", "print(1)"]})
                self.assertTrue(result["ok"])
        finally:
            config.ALLOW_EXEC = False


class TestExecSandbox(IsolatedDBTestCase):
    def test_non_allowlisted_binary_denied(self):
        with self.assertRaises(exec_tools.CommandDeniedError):
            exec_tools.run_command(998, ["curl", "http://example.com"])

    def test_shell_metacharacters_are_inert(self):
        result = exec_tools.run_command(998, ["python3", "-c", "print('safe; rm -rf /')"])
        self.assertIn("safe; rm -rf /", result["stdout"])


if __name__ == "__main__":
    unittest.main()
