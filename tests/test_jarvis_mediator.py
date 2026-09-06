import unittest

from orchestrator import jarvis_mediator
from orchestrator import voice


class TestJarvisMediator(unittest.TestCase):
    def test_detects_gujarati_script(self):
        self.assertEqual(jarvis_mediator.detect_language("સિસ્ટમની સ્થિતિ બતાવો", "en"), "gu")

    def test_detects_hindi_script(self):
        self.assertEqual(jarvis_mediator.detect_language("सिस्टम की स्थिति बताओ", "en"), "hi")

    def test_routes_gujarati_system_status(self):
        intent = voice.detect_intent("શક્તિ સિસ્ટમની સ્થિતિ બતાવો")
        self.assertEqual(intent["action"], "sentinel_check")

    def test_routes_hindi_finance(self):
        intent = voice.detect_intent("शक्ति वित्त रिपोर्ट बताओ")
        self.assertEqual(intent["action"], "finance_report")

    def test_builds_auditable_prompt_without_new_authority(self):
        result = jarvis_mediator.build_prompt(
            "Shakthi, um check system please",
            {"category": "status", "action": "sentinel_check", "args": "um check system please"},
            "en",
        )
        self.assertEqual(result["language"], "en")
        self.assertIn("status/sentinel_check", result["prompt"])
        self.assertIn("never invent", result["prompt"])


if __name__ == "__main__":
    unittest.main()
