"""
Covers the deterministic, offline-testable parts of the Website Builder:
all 7 template types render valid HTML, HTML-escaping actually blocks
injection, and website_builder.py's validation logic. Does NOT exercise
the model-calling pipeline stages (CEO review, requirements generation,
QA review) -- those need live local models and are exercised manually,
the same way every other model-calling pipeline in this system has been.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import component_library as c
from orchestrator import template_registry as tr
from orchestrator import website_builder as wb


class TestTemplateRegistry(unittest.TestCase):
    def test_all_seven_site_types_registered(self):
        self.assertEqual(
            set(tr.TEMPLATES),
            {"landing_page", "business_site", "blog", "saas_ui", "admin_dashboard", "crm_frontend", "internal_tool"},
        )

    def test_every_template_renders_valid_html_with_minimal_requirements(self):
        for site_type in tr.TEMPLATES:
            html = tr.render(site_type, {"business_name": "Test Co"})
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertTrue(html.strip().endswith("</html>"))
            self.assertIn("Test Co", html)

    def test_every_template_renders_with_empty_requirements(self):
        # Every render_* function must supply sensible defaults -- a founder
        # request that produced sparse/failed requirements shouldn't crash
        # the deterministic build step.
        for site_type in tr.TEMPLATES:
            html = tr.render(site_type, {})
            self.assertTrue(html.startswith("<!doctype html>"))

    def test_unknown_site_type_raises(self):
        with self.assertRaises(ValueError):
            tr.render("not_a_real_type", {})

    def test_business_name_xss_is_escaped_across_all_templates(self):
        payload = "<script>alert(1)</script>"
        for site_type in tr.TEMPLATES:
            html = tr.render(site_type, {"business_name": payload})
            self.assertNotIn(payload, html, f"{site_type} did not escape business_name")
            self.assertIn("&lt;script&gt;", html)


class TestComponentLibrary(unittest.TestCase):
    def test_esc_blocks_script_injection(self):
        self.assertNotIn("<script>", c.esc("<script>alert(1)</script>"))

    def test_hero_contains_provided_text(self):
        html = c.hero("Title Here", "Subtitle here", "Click Me")
        self.assertIn("Title Here", html)
        self.assertIn("Subtitle here", html)
        self.assertIn("Click Me", html)

    def test_data_table_escapes_cell_content(self):
        html = c.data_table(["Name"], [["<img src=x onerror=alert(1)>"]])
        self.assertNotIn("<img src=x", html)

    def test_pricing_table_handles_empty_tiers(self):
        html = c.pricing_table([])
        self.assertIsInstance(html, str)  # doesn't raise on empty input


class TestWebsiteBuilderValidation(unittest.TestCase):
    def test_invalid_site_type_rejected_before_any_db_write(self):
        with self.assertRaises(wb.WebsiteBuilderError):
            wb.request_project(1, "not_a_real_site_type", "some request")

    def test_json_block_parsing(self):
        text = '```json\n{"business_name": "Acme", "tagline": "Fast"}\n```'
        parsed = wb._parse_json_block(text)
        self.assertEqual(parsed, {"business_name": "Acme", "tagline": "Fast"})

    def test_json_block_parsing_returns_none_on_malformed(self):
        self.assertIsNone(wb._parse_json_block("```json\n{not valid}\n```"))

    def test_slugify_produces_valid_domain_labels(self):
        # Found live: "Flour & Co." produced "flour-&-co..example.com" --
        # invalid characters and a double dot -- before this fix.
        self.assertEqual(wb._slugify("Flour & Co."), "flour-co")
        self.assertEqual(wb._slugify("Sweet Treats Bakery"), "sweet-treats-bakery")
        self.assertEqual(wb._slugify("!!!"), "site")
        self.assertNotIn("&", wb._slugify("Flour & Co."))
        self.assertNotIn("..", wb._slugify("Flour & Co.") + ".example.com")


if __name__ == "__main__":
    unittest.main()
