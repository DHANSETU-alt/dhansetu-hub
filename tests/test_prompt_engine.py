import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import prompt_engine as pe


class TestRenderPrompt(unittest.TestCase):
    def test_includes_role_and_task(self):
        prompt = pe.render_prompt("claude", "a helpful assistant", "Summarize the input.")
        self.assertIn("You are a helpful assistant.", prompt)
        self.assertIn("Summarize the input.", prompt)

    def test_includes_constraints(self):
        prompt = pe.render_prompt("claude", "role", "task", constraints=["Be concise", "No markdown"])
        self.assertIn("- Be concise", prompt)
        self.assertIn("- No markdown", prompt)

    def test_includes_output_format(self):
        prompt = pe.render_prompt("claude", "role", "task", output_format="PASS or FAIL")
        self.assertIn("PASS or FAIL", prompt)

    def test_unknown_target_raises(self):
        with self.assertRaises(ValueError):
            pe.render_prompt("gpt5", "role", "task")

    def test_llama_gets_brevity_hint_for_long_prompts(self):
        long_task = "x" * 900
        prompt = pe.render_prompt("llama3.2", "role", long_task)
        self.assertIn("brief and direct", prompt)

    def test_short_llama_prompt_has_no_hint(self):
        prompt = pe.render_prompt("llama3.2", "role", "short task")
        self.assertNotIn("brief and direct", prompt)

    def test_all_profiles_are_renderable(self):
        for target in pe.MODEL_PROFILES:
            prompt = pe.render_prompt(target, "role", "task")
            self.assertIn("You are role.", prompt)


class TestLintRolePrompt(unittest.TestCase):
    def test_short_prompt_flagged(self):
        issues = pe.lint_role_prompt("Be nice.")
        self.assertTrue(any("short" in i.lower() for i in issues))

    def test_missing_persona_flagged(self):
        issues = pe.lint_role_prompt("x" * 60)
        self.assertTrue(any("persona" in i.lower() for i in issues))

    def test_well_formed_prompt_has_no_persona_or_length_issues(self):
        good = "You are a QA agent. Reply with PASS or FAIL on the first line, followed by a short reason."
        issues = pe.lint_role_prompt(good)
        self.assertEqual(issues, [])

    def test_long_prompt_without_output_format_flagged(self):
        long_no_format = "You are an agent. " + ("This describes background context. " * 6)
        issues = pe.lint_role_prompt(long_no_format)
        self.assertTrue(any("output-format" in i for i in issues))

    def test_hedgy_prompt_flagged(self):
        issues = pe.lint_role_prompt("You are an agent. It might do this or it might do that depending.")
        self.assertTrue(any("hedge" in i.lower() for i in issues))


class TestOptimizePrompt(unittest.TestCase):
    def test_calls_call_agent_and_returns_structural_issues(self):
        with patch("orchestrator.bug_fixer.call_agent", return_value="Suggested improvement text.") as mock_call:
            result = pe.optimize_prompt(None, 1, "correction_bot", "Be nice.")

        mock_call.assert_called_once()
        self.assertIn("suggestion", result)
        self.assertEqual(result["suggestion"], "Suggested improvement text.")
        self.assertTrue(len(result["structural_issues"]) > 0)


if __name__ == "__main__":
    unittest.main()
