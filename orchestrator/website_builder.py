"""
SHAKTHI WEBSITE BUILDER — pipeline orchestration.

Founder Request -> CEO Review -> Requirements Generator -> Build (deterministic,
template_registry.py) -> QA Review -> Security Review -> Deployment Package.

Reuses existing, unchanged modules rather than reimplementing them: CEO
review goes through ceo.decide() exactly as Bug Fixer and the Audit
pipeline do; Security review reuses security.review()'s site-risk scan
(the same RISKY_SITE_PATTERNS check built for sitegen.py's output);
QA/model calls go through bug_fixer.new_pipeline_task/call_agent, the
same shared helper the Bug Fixer and Audit pipelines already use. Every
model call is logged to the real cost_ledger/task_events, same as
anywhere else in this system -- no parallel cost-tracking invented here.

Every stage updates website_projects.status so the pipeline's progress is
always inspectable mid-flight, not just at the end.
"""
import json
import re
from pathlib import Path

from . import bug_fixer, ceo as ceo_mod, component_library as c, config, db, security, template_registry
from .tools import dispatch

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_SLUG_RE = re.compile(r"[^a-z0-9]+")

VALID_SITE_TYPES = tuple(template_registry.TEMPLATES)


def _slugify(name: str) -> str:
    """A business name has no guarantee of being domain-safe -- found live:
    "Flour & Co." produced "flour-&-co..example.com" (invalid characters,
    a double dot) before this. Collapse every run of non-alphanumeric
    characters to one hyphen instead of a literal space-only replace."""
    slug = _SLUG_RE.sub("-", name.lower()).strip("-")
    return slug or "site"


def _parse_json_block(text: str):
    match = None
    for match in _FENCE_RE.finditer(text):
        pass
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


class WebsiteBuilderError(RuntimeError):
    pass


# --- Stage 1: Founder Request -----------------------------------------------

def request_project(business_id: int, site_type: str, founder_request: str) -> int:
    if site_type not in VALID_SITE_TYPES:
        raise WebsiteBuilderError(f"unknown site_type: {site_type!r}. choices: {VALID_SITE_TYPES}")
    with db.get_conn() as conn:
        project_id = db.insert_website_project(conn, business_id, site_type, founder_request)
    return project_id


# --- Stage 2: CEO Review ----------------------------------------------------

def ceo_review_project(project_id: int) -> dict:
    with db.get_conn() as conn:
        project = db.get_website_project(conn, project_id)
        if not project:
            raise WebsiteBuilderError(f"no such project: {project_id}")

    decision = ceo_mod.decide(
        f"Build a {project['site_type']} website: {project['founder_request']}",
        business_id=project["business_id"],
    )
    approved = decision["status"] == "approved"
    with db.get_conn() as conn:
        db.update_website_project(
            conn, project_id, status="ceo_approved" if approved else "ceo_rejected",
            ceo_decision_id=decision["decision_id"],
        )
    return {"project_id": project_id, "approved": approved, "decision": decision}


# --- Stage 3: Requirements Generator ----------------------------------------

# Each site_type's render_* function reads different fields (see
# template_registry.py) -- a single generic schema meant every non-landing-
# page template either got unused fields or fell back to its hardcoded
# placeholder content. Found live: a real bakery blog request produced a
# real business name but generic "Welcome to our blog" placeholder posts,
# because the old one-size-fits-all prompt asked for "features", which
# render_blog() doesn't read at all -- it needs "posts". Fixed by asking
# for exactly what each template consumes.
REQUIREMENTS_SCHEMA = {
    "landing_page": '{"business_name": "...", "tagline": "...", "cta_text": "...", "contact_email": "...", "features": [{"title": "...", "description": "..."}]}',
    "business_site": '{"business_name": "...", "tagline": "...", "about": "2-3 sentences", "contact_email": "...", "services": [{"title": "...", "description": "..."}]}',
    "blog": '{"business_name": "...", "posts": [{"title": "...", "excerpt": "1 sentence", "date": "YYYY-MM-DD"}]}',
    "saas_ui": '{"business_name": "...", "tagline": "...", "pricing_tiers": [{"name": "...", "price": "...", "features": ["...", "..."]}]}',
    "admin_dashboard": '{"business_name": "...", "stats": [{"label": "...", "value": "..."}], "table_rows": [["id", "name", "status"]]}',
    "crm_frontend": '{"business_name": "...", "contacts": [{"name": "...", "meta": "Lead|Customer|..."}]}',
    "internal_tool": '{"business_name": "...", "items": [{"name": "...", "meta": "status"}]}',
}


def generate_requirements(project_id: int) -> dict:
    with db.get_conn() as conn:
        project = db.get_website_project(conn, project_id)
        if not project:
            raise WebsiteBuilderError(f"no such project: {project_id}")

        schema = REQUIREMENTS_SCHEMA.get(project["site_type"], REQUIREMENTS_SCHEMA["landing_page"])
        task_id = bug_fixer.new_pipeline_task(conn, f"Requirements for website project #{project_id}")
        prompt = (
            f"Founder request: {project['founder_request']}\nSite type: {project['site_type']}\n\n"
            f"Turn this into structured requirements matching this exact shape (3-4 items in any list "
            f"field, all grounded in the founder request, not generic placeholders). Reply with ONLY "
            f"a fenced json block:\n```json\n{schema}\n```\n"
            "Use your best judgement for anything not stated -- do not leave fields empty."
        )
        text = bug_fixer.call_agent(conn, task_id, "website_builder", prompt)
        parsed = _parse_json_block(text)
        db.update_task(conn, task_id, "done" if parsed else "failed", text)

        if parsed is None:
            db.update_website_project(conn, project_id, status="failed")
            return {"project_id": project_id, "parsed": False, "raw": text}

        db.update_website_project(conn, project_id, status="requirements_ready", requirements=json.dumps(parsed))
        return {"project_id": project_id, "parsed": True, "requirements": parsed}


# --- Stage 4: Build (deterministic) -----------------------------------------

def build_site(project_id: int) -> dict:
    with db.get_conn() as conn:
        project = db.get_website_project(conn, project_id)
        if not project:
            raise WebsiteBuilderError(f"no such project: {project_id}")
        if not project["requirements"]:
            raise WebsiteBuilderError(f"project {project_id} has no requirements yet — run generate_requirements first")

        requirements = json.loads(project["requirements"])
        html = template_registry.render(project["site_type"], requirements)

        agent = db.get_agent(conn, "website_builder")
        if not agent:
            raise WebsiteBuilderError("website_builder agent is not registered — run `cli --init`")

        rel_path = f"projects/{project_id}/index.html"
        task_id = bug_fixer.new_pipeline_task(conn, f"Build website project #{project_id}")
        result = dispatch.execute_tool(conn, task_id, agent, project["business_id"], "write_file",
                                        {"path": rel_path, "content": html})
        db.update_task(conn, task_id, "done" if result["ok"] else "failed", str(result))

        if not result["ok"]:
            db.update_website_project(conn, project_id, status="failed")
            raise WebsiteBuilderError(f"write_file failed: {result}")

        local_path = str((config.WORKSPACES_DIR / f"business_{project['business_id']}" / rel_path).resolve())
        domain = f"{_slugify(requirements.get('business_name', 'site'))}.example.com"
        site_id = db.insert_site(conn, project["business_id"], domain, project["site_type"], status="generated")
        db.update_site(conn, site_id, status="generated", local_path=local_path)
        db.update_website_project(conn, project_id, status="built", site_id=site_id)

        return {"project_id": project_id, "site_id": site_id, "local_path": local_path}


# --- Stage 5: QA Review -----------------------------------------------------

def qa_review_project(project_id: int) -> dict:
    with db.get_conn() as conn:
        project = db.get_website_project(conn, project_id)
        if not project or not project["site_id"]:
            raise WebsiteBuilderError(f"project {project_id} has no built site yet — run build_site first")
        site = conn.execute("SELECT * FROM sites WHERE id = ?", (project["site_id"],)).fetchone()
        site = dict(site)
        html = open(site["local_path"]).read()

        task_id = bug_fixer.new_pipeline_task(conn, f"QA review website project #{project_id}")
        prompt = (
            f"Founder request: {project['founder_request']}\n\nGenerated page HTML:\n{html[:4000]}\n\n"
            "Does this page plausibly fulfill the founder's request -- right site type, "
            "has the sections a founder would expect? Reply PASS or FAIL on the first line, "
            "then a short reason."
        )
        text = bug_fixer.call_agent(conn, task_id, "qa", prompt)
        passed = text.strip().upper().startswith("PASS")
        db.update_task(conn, task_id, "done", text)
        db.update_website_project(conn, project_id, status="qa_passed" if passed else "qa_failed", qa_notes=text)
        return {"project_id": project_id, "passed": passed, "notes": text}


# --- Stage 6: Security Review -----------------------------------------------

def security_review_project(project_id: int) -> dict:
    with db.get_conn() as conn:
        project = db.get_website_project(conn, project_id)
        if not project:
            raise WebsiteBuilderError(f"no such project: {project_id}")

    # Reuses security.review()'s existing site-risk scan unchanged -- the
    # same check sitegen.py's output has always been subject to.
    report = security.review(business_id=project["business_id"])
    site_findings = [f for f in report["findings"] if f["type"] in ("secret", "site_risk")]
    passed = len(site_findings) == 0

    with db.get_conn() as conn:
        db.update_website_project(
            conn, project_id, status="security_passed" if passed else "security_failed",
            security_score=report["score"], security_findings=json.dumps(site_findings),
        )
    return {"project_id": project_id, "passed": passed, "score": report["score"], "findings": site_findings}


# --- Stage 7: Deployment Package (deployment_generator.py) -----------------

def run_full_pipeline(business_id: int, site_type: str, founder_request: str) -> dict:
    """Founder Request -> CEO -> Requirements -> Build -> QA -> Security ->
    Package, stopping at the first stage that doesn't pass."""
    from . import deployment_generator

    project_id = request_project(business_id, site_type, founder_request)

    ceo_result = ceo_review_project(project_id)
    if not ceo_result["approved"]:
        return {"project_id": project_id, "stage": "ceo", "ok": False, "detail": ceo_result}

    req_result = generate_requirements(project_id)
    if not req_result["parsed"]:
        return {"project_id": project_id, "stage": "requirements", "ok": False, "detail": req_result}

    build_result = build_site(project_id)

    qa_result = qa_review_project(project_id)
    if not qa_result["passed"]:
        return {"project_id": project_id, "stage": "qa", "ok": False, "detail": qa_result}

    sec_result = security_review_project(project_id)
    if not sec_result["passed"]:
        return {"project_id": project_id, "stage": "security", "ok": False, "detail": sec_result}

    package_result = deployment_generator.create_package(project_id)

    # Correction Bot runs automatically after every packaged site -- review
    # only, never re-gates a pipeline that already passed QA and Security.
    from . import correction_bot
    try:
        html = Path(build_result["local_path"]).read_text()
        correction_bot.review_and_correct("website_content", f"website_builder:project:{project_id}",
                                           html, business_id=business_id)
    except Exception:
        pass

    # Chrome Developer Bot runs automatically after every packaged site
    # too -- a real browser-driven review (SEO/UI/conversion) on top of
    # Correction Bot's content review above. Same non-blocking pattern:
    # a failure here (e.g. `node` unavailable) never fails the build.
    from . import chrome_developer
    try:
        file_url = f"file://{build_result['local_path']}"
        chrome_developer.review_website(file_url, business_id=business_id)
    except Exception:
        pass

    return {"project_id": project_id, "stage": "packaged", "ok": True, "detail": package_result}
