"""
SHAKTHI WEBSITE BUILDER — component library. Deterministic Python functions
that return real, valid HTML/CSS snippets -- same "deterministic where
possible" stance as sitegen.py and security.py's pattern scanner. These
compose into full pages in template_registry.py; nothing here calls a
model. Static, professional-looking output, not framework-wired
interactivity -- see template_registry.py's module docstring for the
honest scope statement on admin_dashboard/crm_frontend/internal_tool.
"""
import html as _html

ACCENT = "#2a6b66"
INK = "#171b18"
MUTED = "#5b6660"
BORDER = "#d8dbd3"
SURFACE = "#ffffff"
BG = "#f4f5f2"


def esc(s) -> str:
    return _html.escape(str(s), quote=True)


def page_shell(title: str, body_html: str, extra_style: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{esc(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, -apple-system, sans-serif; background: {BG}; color: {INK}; line-height: 1.6; }}
  a {{ color: {ACCENT}; text-decoration: none; }}
  .container {{ max-width: 1080px; margin: 0 auto; padding: 0 1.5rem; }}
  {extra_style}
</style>
</head>
<body>
{body_html}
</body>
</html>"""


def navbar(business_name: str, links: list) -> str:
    items = "".join(f'<a href="#{esc(l.lower().replace(" ", "-"))}">{esc(l)}</a>' for l in links)
    return f"""<nav style="background:{SURFACE};border-bottom:1px solid {BORDER};padding:1rem 0;">
  <div class="container" style="display:flex;align-items:center;justify-content:space-between;">
    <strong>{esc(business_name)}</strong>
    <div style="display:flex;gap:1.5rem;font-size:0.9rem;">{items}</div>
  </div>
</nav>"""


def hero(title: str, subtitle: str, cta_text: str = "Get Started") -> str:
    return f"""<header style="padding:5rem 0;text-align:center;">
  <div class="container">
    <h1 style="font-size:2.5rem;margin:0 0 1rem;">{esc(title)}</h1>
    <p style="color:{MUTED};font-size:1.1rem;max-width:60ch;margin:0 auto 2rem;">{esc(subtitle)}</p>
    <a href="#contact" style="background:{ACCENT};color:#fff;padding:0.75rem 1.75rem;border-radius:6px;font-weight:600;">{esc(cta_text)}</a>
  </div>
</header>"""


def feature_grid(features: list) -> str:
    cards = "".join(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:1.5rem;">'
        f'<h3 style="margin:0 0 0.5rem;font-size:1.05rem;">{esc(f.get("title",""))}</h3>'
        f'<p style="margin:0;color:{MUTED};font-size:0.9rem;">{esc(f.get("description",""))}</p></div>'
        for f in features
    )
    return f"""<section class="container" style="padding:3rem 0;">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.25rem;">{cards}</div>
</section>"""


def pricing_table(tiers: list) -> str:
    cards = "".join(
        f'<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:2rem;text-align:center;">'
        f'<h3 style="margin:0 0 0.5rem;">{esc(t.get("name",""))}</h3>'
        f'<div style="font-size:2rem;font-weight:700;margin:0.5rem 0;">{esc(t.get("price",""))}</div>'
        f'<ul style="list-style:none;padding:0;color:{MUTED};font-size:0.9rem;">'
        + "".join(f'<li style="padding:0.25rem 0;">{esc(feat)}</li>' for feat in t.get("features", []))
        + "</ul></div>"
        for t in tiers
    )
    return f"""<section class="container" style="padding:3rem 0;">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.25rem;">{cards}</div>
</section>"""


def contact_form(contact_email: str) -> str:
    return f"""<section id="contact" class="container" style="padding:3rem 0;max-width:480px;">
  <h2 style="font-size:1.4rem;">Contact</h2>
  <p style="color:{MUTED};">Reach us at <a href="mailto:{esc(contact_email)}">{esc(contact_email)}</a></p>
  <form style="display:flex;flex-direction:column;gap:0.75rem;margin-top:1rem;">
    <input type="text" placeholder="Name" style="padding:0.6rem;border:1px solid {BORDER};border-radius:6px;">
    <input type="email" placeholder="Email" style="padding:0.6rem;border:1px solid {BORDER};border-radius:6px;">
    <textarea placeholder="Message" rows="4" style="padding:0.6rem;border:1px solid {BORDER};border-radius:6px;"></textarea>
    <button type="submit" style="background:{ACCENT};color:#fff;border:none;padding:0.7rem;border-radius:6px;font-weight:600;">Send</button>
  </form>
</section>"""


def footer(business_name: str) -> str:
    return f"""<footer style="border-top:1px solid {BORDER};padding:2rem 0;text-align:center;color:{MUTED};font-size:0.85rem;">
  <div class="container">&copy; {esc(business_name)}</div>
</footer>"""


def blog_post_card(title: str, excerpt: str, date: str) -> str:
    return f"""<article style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:1.5rem;margin-bottom:1rem;">
  <div style="color:{MUTED};font-size:0.8rem;">{esc(date)}</div>
  <h2 style="margin:0.4rem 0;font-size:1.3rem;">{esc(title)}</h2>
  <p style="color:{MUTED};margin:0;">{esc(excerpt)}</p>
</article>"""


def sidebar_nav(items: list, active: str = "") -> str:
    links = "".join(
        f'<a href="#" style="display:block;padding:0.6rem 1rem;border-radius:6px;'
        f'{"background:" + ACCENT + ";color:#fff;" if i == active else "color:" + INK + ";"}">{esc(i)}</a>'
        for i in items
    )
    return f"""<aside style="width:220px;background:{SURFACE};border-right:1px solid {BORDER};padding:1.5rem 0.75rem;min-height:100vh;">{links}</aside>"""


def stat_card(label: str, value: str) -> str:
    return f"""<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:1.25rem;">
  <div style="color:{MUTED};font-size:0.75rem;text-transform:uppercase;letter-spacing:0.05em;">{esc(label)}</div>
  <div style="font-size:1.6rem;font-weight:700;margin-top:0.25rem;">{esc(value)}</div>
</div>"""


def data_table(headers: list, rows: list) -> str:
    head = "".join(f'<th style="text-align:left;padding:0.6rem;color:{MUTED};font-size:0.75rem;text-transform:uppercase;">{esc(h)}</th>' for h in headers)
    body = "".join(
        "<tr>" + "".join(f'<td style="padding:0.6rem;border-top:1px solid {BORDER};">{esc(c)}</td>' for c in r) + "</tr>"
        for r in rows
    )
    return f"""<table style="width:100%;border-collapse:collapse;background:{SURFACE};border:1px solid {BORDER};border-radius:8px;overflow:hidden;">
  <thead><tr>{head}</tr></thead>
  <tbody>{body}</tbody>
</table>"""


def login_form(business_name: str) -> str:
    return f"""<div style="max-width:360px;margin:6rem auto;background:{SURFACE};border:1px solid {BORDER};border-radius:8px;padding:2rem;">
  <h2 style="margin:0 0 1.5rem;text-align:center;">{esc(business_name)}</h2>
  <form style="display:flex;flex-direction:column;gap:0.75rem;">
    <input type="email" placeholder="Email" style="padding:0.6rem;border:1px solid {BORDER};border-radius:6px;">
    <input type="password" placeholder="Password" style="padding:0.6rem;border:1px solid {BORDER};border-radius:6px;">
    <button type="submit" style="background:{ACCENT};color:#fff;border:none;padding:0.7rem;border-radius:6px;font-weight:600;">Sign In</button>
  </form>
</div>"""


def record_list(items: list) -> str:
    rows = "".join(
        f'<div style="padding:0.75rem 1rem;border-bottom:1px solid {BORDER};display:flex;justify-content:space-between;">'
        f'<span>{esc(i.get("name",""))}</span><span style="color:{MUTED};font-size:0.85rem;">{esc(i.get("meta",""))}</span></div>'
        for i in items
    )
    return f"""<div style="background:{SURFACE};border:1px solid {BORDER};border-radius:8px;overflow:hidden;">{rows}</div>"""
