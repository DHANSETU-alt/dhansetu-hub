"""
WEB-001: external website audit. Covers the deterministic parsing/scoring
logic offline (fixture HTML, mocked fetch()) -- the actual live HTTP
calls against a real URL are exercised manually, the same way earlier
live-network features (Telegram, Sentinel, Security posture) were proven.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import website_audit as wa

GOOD_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
<title>Dhansetu Hub - Personal Finance Made Simple</title>
<meta name="description" content="Dhansetu Hub helps you track expenses, plan budgets, and reach your savings goals with ease.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://dhansetuhub.in/">
<meta property="og:title" content="Dhansetu Hub">
</head>
<body>
<h1>Welcome to Dhansetu Hub</h1>
<img src="/logo.png" alt="Dhansetu Hub logo">
<img src="/banner.png">
<a href="/about">About</a>
<a href="/pricing">Pricing</a>
<a href="mailto:hello@dhansetuhub.in">Email us</a>
<form><input type="text" id="email"><input type="text"></form>
</body>
</html>"""

BARE_HTML = b"<html><body><p>No head at all.</p></body></html>"


def _parse(body):
    p = wa._PageParser()
    p.feed(body.decode())
    return p


class TestPageParser(unittest.TestCase):
    def test_extracts_title(self):
        p = _parse(GOOD_HTML)
        self.assertEqual(p.title, "Dhansetu Hub - Personal Finance Made Simple")

    def test_extracts_html_lang(self):
        p = _parse(GOOD_HTML)
        self.assertEqual(p.html_lang, "en")

    def test_extracts_canonical(self):
        p = _parse(GOOD_HTML)
        self.assertEqual(p.canonical, "https://dhansetuhub.in/")

    def test_counts_h1(self):
        p = _parse(GOOD_HTML)
        self.assertEqual(p.h1_count, 1)

    def test_image_alt_flags(self):
        p = _parse(GOOD_HTML)
        self.assertEqual(p.image_alt_flags, [True, False])

    def test_collects_links_including_mailto(self):
        p = _parse(GOOD_HTML)
        self.assertIn("/about", p.links)
        self.assertIn("mailto:hello@dhansetuhub.in", p.links)

    def test_bare_html_does_not_crash(self):
        p = _parse(BARE_HTML)
        self.assertEqual(p.title, "")
        self.assertIsNone(p.html_lang)
        self.assertEqual(p.h1_count, 0)


class TestCheckMobileResponsiveness(unittest.TestCase):
    def test_viewport_present(self):
        p = _parse(GOOD_HTML)
        r = wa.check_mobile_responsiveness(p)
        self.assertTrue(r["has_viewport_meta"])

    def test_viewport_absent(self):
        p = _parse(BARE_HTML)
        r = wa.check_mobile_responsiveness(p)
        self.assertFalse(r["has_viewport_meta"])


class TestCheckSeoMetadata(unittest.TestCase):
    def test_good_page_passes_all_seo_checks(self):
        p = _parse(GOOD_HTML)
        r = wa.check_seo_metadata(p)
        self.assertTrue(r["title_length_ok"])
        self.assertTrue(r["description_length_ok"])
        self.assertTrue(r["single_h1"])
        self.assertTrue(r["has_canonical"])
        self.assertTrue(r["has_og_tags"])

    def test_bare_page_fails_seo_checks(self):
        p = _parse(BARE_HTML)
        r = wa.check_seo_metadata(p)
        self.assertIsNone(r["title"])
        self.assertIsNone(r["meta_description"])
        self.assertFalse(r["has_canonical"])


class TestCheckAccessibility(unittest.TestCase):
    def test_flags_missing_alt_and_unlabeled_inputs(self):
        p = _parse(GOOD_HTML)
        r = wa.check_accessibility(p)
        self.assertEqual(r["images_missing_alt"], 1)
        self.assertEqual(r["form_inputs_unlabeled"], 1)
        self.assertTrue(r["html_lang_present"])

    def test_bare_page_has_no_lang(self):
        p = _parse(BARE_HTML)
        r = wa.check_accessibility(p)
        self.assertFalse(r["html_lang_present"])


class TestCheckHttps(unittest.TestCase):
    def test_https_url_successful_fetch_is_valid(self):
        r = wa.check_https("https://example.com", {"ok": True})
        self.assertTrue(r["uses_https"])
        self.assertTrue(r["cert_valid"])

    def test_http_url_is_flagged(self):
        r = wa.check_https("http://example.com", {"ok": True})
        self.assertFalse(r["uses_https"])
        self.assertIsNone(r["cert_valid"])

    def test_https_url_failed_fetch_is_invalid(self):
        r = wa.check_https("https://example.com", {"ok": False})
        self.assertTrue(r["uses_https"])
        self.assertFalse(r["cert_valid"])


class TestCheckSecurityHeaders(unittest.TestCase):
    def test_counts_present_headers(self):
        result = {"headers": {"Strict-Transport-Security": "max-age=63072000", "X-Frame-Options": "DENY"}}
        r = wa.check_security_headers(result)
        self.assertEqual(r["present_count"], 2)
        self.assertIn("X-Content-Type-Options", r["missing"])

    def test_no_headers_present(self):
        r = wa.check_security_headers({"headers": {}})
        self.assertEqual(r["present_count"], 0)
        self.assertEqual(len(r["missing"]), 5)


class TestCheckSitemapAndRobots(unittest.TestCase):
    def test_sitemap_present_and_valid(self):
        with patch.object(wa, "fetch", return_value={"ok": True, "status": 200, "body": b"<urlset></urlset>"}):
            r = wa.check_sitemap("https://example.com")
        self.assertTrue(r["present"])
        self.assertTrue(r["looks_valid"])

    def test_sitemap_missing(self):
        with patch.object(wa, "fetch", return_value={"ok": False, "status": 404, "body": b""}):
            r = wa.check_sitemap("https://example.com")
        self.assertFalse(r["present"])
        self.assertFalse(r["looks_valid"])

    def test_robots_present_with_sitemap_reference(self):
        body = b"User-agent: *\nDisallow: /admin\nSitemap: https://example.com/sitemap.xml\n"
        with patch.object(wa, "fetch", return_value={"ok": True, "status": 200, "body": body}):
            r = wa.check_robots_txt("https://example.com")
        self.assertTrue(r["present"])
        self.assertTrue(r["references_sitemap"])
        self.assertFalse(r["disallows_everything"])

    def test_robots_disallows_everything(self):
        body = b"User-agent: *\nDisallow: /\n"
        with patch.object(wa, "fetch", return_value={"ok": True, "status": 200, "body": body}):
            r = wa.check_robots_txt("https://example.com")
        self.assertTrue(r["disallows_everything"])


class TestCheckBrokenLinks(unittest.TestCase):
    def test_dedupes_and_skips_mailto(self):
        p = _parse(GOOD_HTML)
        with patch.object(wa, "fetch", return_value={"ok": True, "status": 200, "body": b""}):
            r = wa.check_broken_links("https://dhansetuhub.in", p)
        self.assertEqual(r["checked"], 2)  # /about, /pricing -- mailto: skipped
        self.assertEqual(r["broken_count"], 0)

    def test_broken_link_flagged(self):
        p = _parse(GOOD_HTML)
        def fake_fetch(url, method="GET", timeout=None):
            if "pricing" in url:
                return {"ok": False, "status": 404, "body": b"", "error": "Not Found"}
            return {"ok": True, "status": 200, "body": b""}
        with patch.object(wa, "fetch", side_effect=fake_fetch):
            r = wa.check_broken_links("https://dhansetuhub.in", p)
        self.assertEqual(r["broken_count"], 1)
        self.assertIn("pricing", r["broken"][0]["url"])

    def test_respects_max_links_cap(self):
        p = wa._PageParser()
        p.feed("".join(f'<a href="/page{i}">p</a>' for i in range(60)))
        with patch.object(wa, "fetch", return_value={"ok": True, "status": 200, "body": b""}):
            r = wa.check_broken_links("https://example.com", p)
        self.assertLessEqual(r["checked"], 25)
        self.assertGreater(r["skipped_beyond_cap"], 0)


class TestComputeScores(unittest.TestCase):
    def _all_good(self):
        p = _parse(GOOD_HTML)
        load = {"loaded": True, "response_time_ms": 400}
        https = {"uses_https": True, "cert_valid": True}
        mobile = wa.check_mobile_responsiveness(p)
        seo = wa.check_seo_metadata(p)
        a11y = {"images_missing_alt": 0, "html_lang_present": True}
        headers = {"present_count": 5, "total": 5}
        links = {"checked": 2, "broken_count": 0}
        sitemap = {"present": True}
        robots = {"present": True}
        return load, https, mobile, seo, a11y, headers, links, sitemap, robots

    def test_perfect_site_scores_high(self):
        load, https, mobile, seo, a11y, headers, links, sitemap, robots = self._all_good()
        scores = wa.compute_scores(load, https, mobile, seo, load, links, a11y, headers, sitemap, robots)
        self.assertEqual(scores["security_score"], 100)
        self.assertGreaterEqual(scores["website_health_score"], 90)
        self.assertEqual(scores["performance_score"], 100)

    def test_broken_site_scores_low(self):
        load = {"loaded": False, "response_time_ms": 9000}
        https = {"uses_https": False, "cert_valid": None}
        p = _parse(BARE_HTML)
        mobile = wa.check_mobile_responsiveness(p)
        seo = wa.check_seo_metadata(p)
        a11y = {"images_missing_alt": 3, "html_lang_present": False}
        headers = {"present_count": 0, "total": 5}
        links = {"checked": 10, "broken_count": 8}
        sitemap = {"present": False}
        robots = {"present": False}
        scores = wa.compute_scores(load, https, mobile, seo, load, links, a11y, headers, sitemap, robots)
        self.assertLess(scores["website_health_score"], 50)
        self.assertLess(scores["security_score"], 50)
        self.assertEqual(scores["performance_score"], 30)

    def test_scores_always_within_bounds(self):
        load, https, mobile, seo, a11y, headers, links, sitemap, robots = self._all_good()
        scores = wa.compute_scores(load, https, mobile, seo, load, links, a11y, headers, sitemap, robots)
        for v in scores.values():
            self.assertGreaterEqual(v, 0)
            self.assertLessEqual(v, 100)


class TestFormatReport(unittest.TestCase):
    def test_report_contains_all_required_scores(self):
        scores = {"website_health_score": 88, "seo_score": 90, "security_score": 70, "performance_score": 100}
        load = {"loaded": True, "response_time_ms": 350}
        https = {"uses_https": True, "cert_valid": True}
        links = {"checked": 5, "broken_count": 0}
        headers = {"present_count": 3, "total": 5}
        text = wa.format_report("https://dhansetuhub.in", scores, load, https, links, headers, "2026-01-01 00:00:00 UTC")
        self.assertIn("SHAKTHI WEBSITE AUDIT REPORT", text)
        self.assertIn("Website Health Score: 88/100", text)
        self.assertIn("SEO Score: 90/100", text)
        self.assertIn("Security Score: 70/100", text)
        self.assertIn("Performance Score: 100/100", text)
        self.assertIn("HTTPS: Yes", text)


if __name__ == "__main__":
    unittest.main()
