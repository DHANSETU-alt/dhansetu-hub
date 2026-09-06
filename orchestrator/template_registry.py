"""
SHAKTHI WEBSITE BUILDER — template registry. 7 site types, each a function
that composes component_library.py snippets into a full page from a
requirements dict.

Honest scope: admin_dashboard, crm_frontend, and internal_tool produce
real, valid, professional-looking STATIC HTML/CSS UI -- not wired-up
functional applications with live data or a backend. Building 7 types of
actual working full-stack apps would be a different, much larger project
than a website builder (it's what this system's own Next.js dashboard IS,
for this system specifically) -- these are static mockups/scaffolds a
founder can hand to a real frontend build, the same honest scoping
sitegen.py already applied to landing pages in Phase 0.2.

This does NOT touch templates/template_landing_v1/ or sitegen.py -- that
foundation is unchanged, still reachable via --generate-site. This is a
parallel, richer pipeline for the 6 new site types plus a second,
component-composed landing page option.
"""
from . import component_library as c


def _get(req: dict, key: str, default):
    return req.get(key) or default


def render_landing_page(req: dict) -> str:
    name = _get(req, "business_name", "Your Business")
    body = (
        c.hero(name, _get(req, "tagline", f"Welcome to {name}."), _get(req, "cta_text", "Get Started"))
        + c.feature_grid(_get(req, "features", [{"title": "Fast", "description": "Built for speed."},
                                                  {"title": "Reliable", "description": "Always available."},
                                                  {"title": "Simple", "description": "Easy to use."}]))
        + c.contact_form(_get(req, "contact_email", "hello@example.com"))
        + c.footer(name)
    )
    return c.page_shell(name, body)


def render_business_site(req: dict) -> str:
    name = _get(req, "business_name", "Your Business")
    links = ["About", "Services", "Contact"]
    body = (
        c.navbar(name, links)
        + c.hero(name, _get(req, "tagline", f"{name} — professional services you can trust."), "Contact Us")
        + f'<section id="about" class="container" style="padding:2rem 0;"><h2>About</h2><p style="color:{c.MUTED};max-width:70ch;">{c.esc(_get(req, "about", f"{name} has been serving customers with dedication and care."))}</p></section>'
        + c.feature_grid(_get(req, "services", [{"title": "Consulting", "description": "Expert guidance."},
                                                   {"title": "Support", "description": "We're here to help."},
                                                   {"title": "Delivery", "description": "On time, every time."}]))
        + c.contact_form(_get(req, "contact_email", "hello@example.com"))
        + c.footer(name)
    )
    return c.page_shell(name, body)


def render_blog(req: dict) -> str:
    name = _get(req, "business_name", "The Blog")
    posts = _get(req, "posts", [
        {"title": "Welcome to our blog", "excerpt": "This is where we'll share updates and insights.", "date": "2026-01-01"},
        {"title": "Getting started", "excerpt": "A quick guide to what we do and why it matters.", "date": "2026-01-08"},
    ])
    body = (
        c.navbar(name, ["Home", "Archive"])
        + f'<div class="container" style="padding:2rem 0;max-width:680px;">'
        + "".join(c.blog_post_card(p.get("title", ""), p.get("excerpt", ""), p.get("date", "")) for p in posts)
        + "</div>"
        + c.footer(name)
    )
    return c.page_shell(name, body)


def render_saas_ui(req: dict) -> str:
    name = _get(req, "business_name", "Your SaaS")
    body = (
        c.navbar(name, ["Product", "Pricing", "Login"])
        + c.hero(name, _get(req, "tagline", "The tool your team will actually use."), "Start Free Trial")
        + c.pricing_table(_get(req, "pricing_tiers", [
            {"name": "Starter", "price": "$0", "features": ["1 user", "Basic features"]},
            {"name": "Pro", "price": "$29/mo", "features": ["Unlimited users", "All features", "Priority support"]},
        ]))
        + c.footer(name)
    )
    return c.page_shell(name, body)


def render_admin_dashboard(req: dict) -> str:
    name = _get(req, "business_name", "Admin")
    stats = _get(req, "stats", [{"label": "Users", "value": "1,204"}, {"label": "Revenue", "value": "$12,400"},
                                  {"label": "Open Tickets", "value": "7"}])
    table_rows = _get(req, "table_rows", [["#1", "Sample Row", "Active"], ["#2", "Another Row", "Pending"]])
    stat_html = "".join(c.stat_card(s.get("label", ""), s.get("value", "")) for s in stats)
    body = f"""<div style="display:flex;">
{c.sidebar_nav(["Overview", "Users", "Settings"], active="Overview")}
<main class="container" style="padding:2rem;flex:1;">
  <h1 style="font-size:1.4rem;">{c.esc(name)} — Overview</h1>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin:1.5rem 0;">{stat_html}</div>
  {c.data_table(["ID", "Name", "Status"], table_rows)}
</main>
</div>"""
    return c.page_shell(f"{name} — Admin", body)


def render_crm_frontend(req: dict) -> str:
    name = _get(req, "business_name", "CRM")
    contacts = _get(req, "contacts", [
        {"name": "Sample Contact 1", "meta": "Lead"}, {"name": "Sample Contact 2", "meta": "Customer"},
    ])
    body = f"""<div style="display:flex;">
{c.sidebar_nav(["Contacts", "Deals", "Tasks"], active="Contacts")}
<main class="container" style="padding:2rem;flex:1;">
  <h1 style="font-size:1.4rem;">{c.esc(name)} — Contacts</h1>
  <div style="margin-top:1.5rem;">{c.record_list(contacts)}</div>
</main>
</div>"""
    return c.page_shell(f"{name} — CRM", body)


def render_internal_tool(req: dict) -> str:
    name = _get(req, "business_name", "Internal Tool")
    items = _get(req, "items", [{"name": "Sample Item 1", "meta": "queued"}, {"name": "Sample Item 2", "meta": "done"}])
    body = f"""<div style="display:flex;">
{c.sidebar_nav(["Queue", "History"], active="Queue")}
<main class="container" style="padding:2rem;flex:1;max-width:680px;">
  <h1 style="font-size:1.4rem;">{c.esc(name)}</h1>
  <div style="margin-top:1.5rem;">{c.record_list(items)}</div>
</main>
</div>"""
    return c.page_shell(name, body)


TEMPLATES = {
    "landing_page": render_landing_page,
    "business_site": render_business_site,
    "blog": render_blog,
    "saas_ui": render_saas_ui,
    "admin_dashboard": render_admin_dashboard,
    "crm_frontend": render_crm_frontend,
    "internal_tool": render_internal_tool,
}


def render(site_type: str, requirements: dict) -> str:
    fn = TEMPLATES.get(site_type)
    if not fn:
        raise ValueError(f"unknown site_type: {site_type!r}. choices: {sorted(TEMPLATES)}")
    return fn(requirements)
