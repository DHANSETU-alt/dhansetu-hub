"""
SHAKTHI Chrome Developer Bot -- advanced SEO analysis.

Deliberately NOT a rewrite of website_audit.py's existing SEO checks
(title/description/canonical/h1 count, already built and tested for
WEB-001) -- reuses that module's _PageParser directly rather than parsing
HTML a second way, and adds checks that module doesn't do: heading
hierarchy (not just an h1 count), structured data (JSON-LD), full Open
Graph completeness (title+description+image, not just og:title
presence), and a basic title/h1 keyword-overlap heuristic. Two SEO
checkers that quietly drifted apart would be worse than one file that's
honest about only adding what's new.
"""
import html.parser
import re

from . import website_audit as wa


class _HeadingParser(html.parser.HTMLParser):
    """Collects the heading sequence (h1-h6, in document order) plus
    JSON-LD and full OG tag data -- the things website_audit.py's parser
    doesn't track."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings = []          # [(level, text_so_far)]
        self.og = {}
        self.json_ld_blocks = []
        self._current_heading_level = None
        self._in_json_ld = False
        self._json_ld_buffer = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if re.fullmatch(r"h[1-6]", tag):
            self._current_heading_level = int(tag[1])
            self.headings.append([self._current_heading_level, ""])
        elif tag == "meta" and d.get("property", "").startswith("og:"):
            self.og[d["property"]] = d.get("content", "")
        elif tag == "script" and d.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_buffer = ""

    def handle_endtag(self, tag):
        if re.fullmatch(r"h[1-6]", tag):
            self._current_heading_level = None
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            if self._json_ld_buffer.strip():
                self.json_ld_blocks.append(self._json_ld_buffer.strip())

    def handle_data(self, data):
        if self._current_heading_level is not None and self.headings:
            self.headings[-1][1] += data
        if self._in_json_ld:
            self._json_ld_buffer += data


def _keyword_overlap(title: str, h1_text: str) -> float:
    """Fraction of significant title words (len > 3) that also appear in
    the h1 -- a basic, honest proxy for topical consistency, not a real
    keyword-research tool."""
    title_words = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", title)}
    if not title_words:
        return 1.0  # nothing to check against -- don't penalize
    h1_words = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", h1_text)}
    overlap = title_words & h1_words
    return len(overlap) / len(title_words)


def analyze(html_content: str) -> dict:
    page = wa._PageParser()
    heading_page = _HeadingParser()
    try:
        page.feed(html_content)
    except Exception:
        pass
    try:
        heading_page.feed(html_content)
    except Exception:
        pass

    base_seo = wa.check_seo_metadata(page)

    heading_levels = [h[0] for h in heading_page.headings]
    hierarchy_ok = True
    for i in range(1, len(heading_levels)):
        if heading_levels[i] - heading_levels[i - 1] > 1:
            hierarchy_ok = False
            break

    og_complete = all(k in heading_page.og and heading_page.og[k] for k in ("og:title", "og:description", "og:image"))

    h1_text = next((t for lvl, t in heading_page.headings if lvl == 1), "")
    keyword_overlap = _keyword_overlap(base_seo["title"] or "", h1_text)

    return {
        **base_seo,
        "heading_sequence": heading_levels,
        "heading_hierarchy_ok": hierarchy_ok,
        "og_tags_present": heading_page.og,
        "og_complete": og_complete,
        "has_structured_data": len(heading_page.json_ld_blocks) > 0,
        "structured_data_blocks": len(heading_page.json_ld_blocks),
        "title_h1_keyword_overlap": round(keyword_overlap, 2),
    }


def seo_score(analysis: dict) -> int:
    earned = sum([
        bool(analysis["title"]) and analysis["title_length_ok"],
        bool(analysis["meta_description"]) and analysis["description_length_ok"],
        analysis["single_h1"],
        analysis["has_canonical"],
        analysis["heading_hierarchy_ok"],
        analysis["og_complete"],
        analysis["has_structured_data"],
        analysis["title_h1_keyword_overlap"] >= 0.5,
    ])
    return max(0, min(100, round(100 * earned / 8)))


def seo_findings(analysis: dict) -> list:
    findings = []
    if not analysis["title"]:
        findings.append(("seo", "P1", "Missing <title> tag."))
    if not analysis["meta_description"]:
        findings.append(("seo", "P2", "Missing meta description."))
    if not analysis["single_h1"]:
        findings.append(("seo", "P3", f"Found {analysis['h1_count']} <h1> tags (expected exactly 1)."))
    if not analysis["heading_hierarchy_ok"]:
        findings.append(("seo", "P3", f"Heading levels skip a level (sequence: {analysis['heading_sequence']}) — confuses screen readers and search crawlers."))
    if not analysis["og_complete"]:
        missing = [k for k in ("og:title", "og:description", "og:image") if not analysis["og_tags_present"].get(k)]
        findings.append(("seo", "P2", f"Incomplete Open Graph tags — missing: {', '.join(missing)}."))
    if not analysis["has_structured_data"]:
        findings.append(("seo", "P3", "No JSON-LD structured data found — search engines get less context about the page."))
    if analysis["title_h1_keyword_overlap"] < 0.5:
        findings.append(("seo", "P3", f"Title and H1 share only {analysis['title_h1_keyword_overlap']*100:.0f}% of significant words — may look topically inconsistent to search engines."))
    return findings
