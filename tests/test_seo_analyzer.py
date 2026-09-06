import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import seo_analyzer

GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<title>Dhansetu Hub - Personal Finance Tools</title>
<meta name="description" content="Dhansetu Hub helps you track expenses, plan budgets, and reach your savings goals with ease.">
<link rel="canonical" href="https://dhansetuhub.in/">
<meta property="og:title" content="Dhansetu Hub">
<meta property="og:description" content="Personal finance tools for everyone.">
<meta property="og:image" content="https://dhansetuhub.in/og.png">
<script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization"}</script>
</head>
<body>
<h1>Dhansetu Hub Finance Tools</h1>
<h2>Features</h2>
<h3>Budgeting</h3>
</body>
</html>"""

BAD_HIERARCHY_HTML = """<html><head><title>Test Site Homepage</title></head>
<body><h1>Home</h1><h3>Skipped h2</h3></body></html>"""

BARE_HTML = "<html><body><p>nothing here</p></body></html>"


class TestAnalyze(unittest.TestCase):
    def test_good_page_passes_everything(self):
        a = seo_analyzer.analyze(GOOD_HTML)
        self.assertTrue(a["heading_hierarchy_ok"])
        self.assertTrue(a["og_complete"])
        self.assertTrue(a["has_structured_data"])
        self.assertGreaterEqual(a["title_h1_keyword_overlap"], 0.5)

    def test_detects_skipped_heading_level(self):
        a = seo_analyzer.analyze(BAD_HIERARCHY_HTML)
        self.assertFalse(a["heading_hierarchy_ok"])

    def test_bare_page_has_no_og_or_structured_data(self):
        a = seo_analyzer.analyze(BARE_HTML)
        self.assertFalse(a["og_complete"])
        self.assertFalse(a["has_structured_data"])

    def test_incomplete_og_tags_flagged(self):
        html = '<html><head><title>Test Site Homepage</title><meta property="og:title" content="Test"></head><body><h1>Test Site</h1></body></html>'
        a = seo_analyzer.analyze(html)
        self.assertFalse(a["og_complete"])
        self.assertIn("og:title", a["og_tags_present"])
        self.assertNotIn("og:description", a["og_tags_present"])


class TestKeywordOverlap(unittest.TestCase):
    def test_matching_words_scored_high(self):
        overlap = seo_analyzer._keyword_overlap("Dhansetu Hub Finance Tools", "Dhansetu Hub Finance Tools Homepage")
        self.assertGreaterEqual(overlap, 0.75)

    def test_no_overlap_scored_low(self):
        overlap = seo_analyzer._keyword_overlap("Completely Different Words Here", "Totally Unrelated Content Below")
        self.assertEqual(overlap, 0.0)

    def test_empty_title_does_not_penalize(self):
        self.assertEqual(seo_analyzer._keyword_overlap("", "Some Heading"), 1.0)


class TestSeoScore(unittest.TestCase):
    def test_perfect_analysis_scores_100(self):
        a = seo_analyzer.analyze(GOOD_HTML)
        score = seo_analyzer.seo_score(a)
        self.assertEqual(score, 100)

    def test_bare_page_scores_low(self):
        a = seo_analyzer.analyze(BARE_HTML)
        score = seo_analyzer.seo_score(a)
        self.assertLess(score, 40)

    def test_score_always_within_bounds(self):
        for html in (GOOD_HTML, BAD_HIERARCHY_HTML, BARE_HTML):
            a = seo_analyzer.analyze(html)
            score = seo_analyzer.seo_score(a)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)


class TestSeoFindings(unittest.TestCase):
    def test_good_page_has_no_findings(self):
        a = seo_analyzer.analyze(GOOD_HTML)
        findings = seo_analyzer.seo_findings(a)
        self.assertEqual(findings, [])

    def test_bare_page_flags_missing_title_and_description(self):
        a = seo_analyzer.analyze(BARE_HTML)
        findings = seo_analyzer.seo_findings(a)
        categories = [f[2] for f in findings]
        self.assertTrue(any("title" in c.lower() for c in categories))
        self.assertTrue(any("description" in c.lower() for c in categories))


if __name__ == "__main__":
    unittest.main()
