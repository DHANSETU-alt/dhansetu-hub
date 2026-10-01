"""
2026-09-13: the founder installed 25 real generic-purpose agent skills
(~/.agents/skills/, from addyosmani/agent-skills via `npx skills add`) and
asked for Shakthi_OS's own agents to be able to draw on them. Before this,
routing.run_task() (Shakthi_OS's local-model agent dispatch) had no way to
reach that content at all -- it's plain markdown authored for a different
kind of harness. skills_library.py exposes it; run_task()'s `skill_hint`
param opts one specific task into one specific skill's guidance.

Tests here use a temporary skills directory (not the real
~/.agents/skills/) so this suite doesn't depend on what happens to be
installed on the machine running it.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import db, model_gateway, routing, skills_library


class TestSkillsLibrary(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_skills_test_")
        skill_dir = Path(self._tmp_dir) / "example-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: A test skill for verification.\n---\n\n"
            "# Example Skill\n\nDo the thing carefully.\n"
        )
        # a directory with no SKILL.md must be silently skipped, not error
        (Path(self._tmp_dir) / "not-a-skill").mkdir()
        self._orig_dir = skills_library.SKILLS_DIR
        skills_library.SKILLS_DIR = Path(self._tmp_dir)

    def tearDown(self):
        import shutil
        skills_library.SKILLS_DIR = self._orig_dir
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_list_skills_reads_frontmatter(self):
        skills = skills_library.list_skills()
        self.assertEqual(skills, [{"name": "example-skill", "description": "A test skill for verification."}])

    def test_load_skill_returns_body_without_frontmatter(self):
        body = skills_library.load_skill("example-skill")
        self.assertIn("Do the thing carefully.", body)
        self.assertNotIn("description:", body)

    def test_load_skill_missing_returns_none(self):
        self.assertIsNone(skills_library.load_skill("does-not-exist"))

    def test_list_skills_on_missing_directory_returns_empty(self):
        skills_library.SKILLS_DIR = Path(self._tmp_dir) / "nonexistent"
        self.assertEqual(skills_library.list_skills(), [])


class TestRunTaskSkillHint(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_skills_routing_test_")
        skill_dir = Path(self._tmp_dir) / "example-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: test\n---\n\nSKILL-BODY-MARKER\n"
        )
        self._orig_skills_dir = skills_library.SKILLS_DIR
        skills_library.SKILLS_DIR = Path(self._tmp_dir)

        self._orig_db_path = db.config.DB_PATH
        self._db_tmp_dir = tempfile.mkdtemp(prefix="shakthi_skills_routing_db_")
        db.config.DB_PATH = f"{self._db_tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        skills_library.SKILLS_DIR = self._orig_skills_dir
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        shutil.rmtree(self._db_tmp_dir, ignore_errors=True)

    def test_skill_hint_folds_skill_body_into_the_prompt_sent_to_the_model(self):
        captured = {}

        def fake_call_local(model, role_prompt, prompt):
            captured["prompt"] = prompt
            return ("ok", 10, 5)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local):
            result = routing.run_task("engineer", "review this diff", skill_hint="example-skill")

        # QA may or may not pass a trivial fake "ok" response -- irrelevant
        # to what this test verifies, which is only that the skill body
        # reached the model's prompt.
        self.assertIn(result["status"], ("done", "done_local_fallback"))
        self.assertIn("SKILL-BODY-MARKER", captured["prompt"])
        self.assertIn("review this diff", captured["prompt"])

    def test_unknown_skill_hint_raises(self):
        with self.assertRaises(ValueError):
            routing.run_task("engineer", "review this diff", skill_hint="not-a-real-skill")

    def test_no_skill_hint_is_unaffected(self):
        """Existing callers that never pass skill_hint see no behavior
        change at all -- this must stay purely additive."""
        captured = {}

        def fake_call_local(model, role_prompt, prompt):
            captured["prompt"] = prompt
            return ("ok", 10, 5)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local):
            routing.run_task("engineer", "review this diff")

        self.assertNotIn("SKILL-BODY-MARKER", captured["prompt"])


if __name__ == "__main__":
    unittest.main()
