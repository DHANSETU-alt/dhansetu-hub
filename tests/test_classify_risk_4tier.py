"""
Founder Command Center (Task 13) needed a real 4-tier priority
(low/normal/high/critical) instead of the original 2-tier
(normal/critical), so classify_risk() was extended. Real constraint this
locks in: CRITICAL_KEYWORDS and the run_task() cloud-escalation gate
(`risk == "critical"`) must be byte-for-byte unchanged -- the extension
only adds new bands for goals that don't hit a critical keyword.

A real regression was caught here during that change: a first pass at
HIGH_KEYWORDS/LOW_KEYWORDS used bare generic words ("security", "check")
that collided with test_v4.py's test_founder_examples_are_not_critical
(real founder voice commands like "security audit start karo" must stay
"normal"). The keyword lists were narrowed to multi-word phrases for
exactly that reason -- these tests guard against that regression
reappearing.
"""
import unittest

from orchestrator import routing


class TestClassifyRisk4Tier(unittest.TestCase):
    def test_critical_unchanged(self):
        self.assertEqual(routing.classify_risk("please refund this customer"), "critical")
        self.assertEqual(routing.classify_risk("delete all records in production database"), "critical")

    def test_high_needs_specific_phrase(self):
        self.assertEqual(routing.classify_risk("let's deploy to production tonight"), "high")
        self.assertEqual(routing.classify_risk("we should go live with the new pricing"), "high")

    def test_low_needs_specific_phrase(self):
        self.assertEqual(routing.classify_risk("this is just a draft, don't act on it"), "low")

    def test_generic_verbs_stay_normal_not_high_or_low(self):
        # The real regression: bare "security"/"check"/"review" must not
        # reclassify ordinary read-only status commands.
        self.assertEqual(routing.classify_risk("Shakthi security audit start karo"), "normal")
        self.assertEqual(routing.classify_risk("Shakthi mara websites check kar"), "normal")
        self.assertEqual(routing.classify_risk("please review the report"), "normal")

    def test_critical_keyword_wins_over_high_or_low(self):
        # A goal that could plausibly match more than one band must still
        # resolve to critical -- critical is checked first, unconditionally.
        self.assertEqual(routing.classify_risk("deploy to production and cancel subscription for this legal contract"), "critical")


if __name__ == "__main__":
    unittest.main()
