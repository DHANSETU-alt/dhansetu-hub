"""
Real tests for the Dhansetu AI course-selling branch -- separate from
sales.py/marketing.py entirely. Model calls mocked (no live Ollama
dependency), same pattern as test_sales.py/test_marketing.py.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import dhansetu_ai, db, model_gateway, routing


class DhansetuTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_dhansetu_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()
        from orchestrator import registry
        registry.sync_registry()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_course(self, title="Excel Basics for Small Shops"):
        with db.get_conn() as conn:
            return db.insert_course(conn, None, title)


class TestDraftCourse(DhansetuTestBase):
    def test_parses_outline_and_sales_copy(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("OUTLINE:\nModule 1: Basics\nModule 2: Formulas\n\n"
                    "SALES COPY:\nLearn Excel fast, built for small shop owners.", 20, 15)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = dhansetu_ai.draft_course(course_id)

        self.assertIn("Module 1", result["outline"])
        self.assertIn("small shop owners", result["sales_copy"])

        with db.get_conn() as conn:
            course = db.get_course(conn, course_id)
        self.assertEqual(course["status"], "ready")

    def test_unparseable_output_falls_back_to_raw_text_not_lost(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("Just some free-form course description with no headers.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = dhansetu_ai.draft_course(course_id)

        self.assertIsNone(result["outline"])
        self.assertIn("free-form course description", result["sales_copy"])

    def test_creates_real_course_writer_task(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("OUTLINE:\nA\n\nSALES COPY:\nB", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            dhansetu_ai.draft_course(course_id)

        with db.get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE agent_id = 'course_writer'").fetchone()["c"]
        self.assertEqual(count, 1)


class TestVisualPromptAndReelScript(DhansetuTestBase):
    def test_write_visual_prompt_stores_in_content_queue(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("Glowing chalk dust swirling around a hand writing on a blackboard, warm light.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = dhansetu_ai.write_visual_prompt(course_id)

        with db.get_conn() as conn:
            content = db.get_content(conn, result["content_id"])
        self.assertEqual(content["content_type"], "visual_prompt")
        self.assertEqual(content["platform"], "instagram")

    def test_write_reel_script_stores_in_content_queue(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("0-2s: hook line\n2-8s: main point\n8-10s: CTA", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            result = dhansetu_ai.write_reel_script(course_id)

        with db.get_conn() as conn:
            content = db.get_content(conn, result["content_id"])
        self.assertEqual(content["content_type"], "reel_script")


class TestSchedulePost(DhansetuTestBase):
    def test_marks_ready_to_post_never_calls_a_real_posting_api(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("Glow prompt text.", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            visual = dhansetu_ai.write_visual_prompt(course_id)

            def fake_scheduler_call(model, role_prompt, prompt):
                return ("Ready-to-post caption with #hashtags", 10, 10)

            with patch.object(model_gateway, "call_local", side_effect=fake_scheduler_call):
                result = dhansetu_ai.schedule_post(visual["content_id"])

        self.assertEqual(result["status"], "ready_to_post")
        with db.get_conn() as conn:
            original = db.get_content(conn, visual["content_id"])
            caption = db.get_content(conn, result["caption_content_id"])
        self.assertEqual(original["status"], "ready_to_post")
        self.assertEqual(caption["content_type"], "instagram_post")
        self.assertEqual(caption["platform"], "instagram")

    def test_list_ready_to_post_filters_by_platform(self):
        course_id = self._make_course()

        def fake_call_local(model, role_prompt, prompt):
            return ("some content", 10, 10)

        with patch.object(model_gateway, "call_local", side_effect=fake_call_local), \
             patch.object(routing, "_validate", return_value=(True, "PASS")):
            visual = dhansetu_ai.write_visual_prompt(course_id)
            dhansetu_ai.schedule_post(visual["content_id"], platform="instagram")

        ready = dhansetu_ai.list_ready_to_post(platform="instagram")
        self.assertGreaterEqual(len(ready), 1)
        self.assertTrue(all(r["platform"] == "instagram" for r in ready))


class TestMarketingUnaffected(DhansetuTestBase):
    def test_marketing_content_queue_rows_have_no_platform_by_default(self):
        """The whole point of sharing content_queue -- marketing.py's own
        calls never set platform, so its existing rows/behavior are
        completely unaffected by this module existing."""
        with db.get_conn() as conn:
            content_id = db.insert_content(conn, None, "landing_copy", "A", "core_offer", "some marketing copy", 0.8)
            content = db.get_content(conn, content_id)
        self.assertIsNone(content["platform"])


if __name__ == "__main__":
    unittest.main()
