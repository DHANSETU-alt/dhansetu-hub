"""
Deterministic Website Builder foundation. Does NOT depend on a local model
reliably emitting a correct tool call -- template + substitution + write,
through the same execute_tool() choke point every model-driven call uses,
attributed to agent_id="website_builder". One choke point for every file
write in the system, deterministic or model-driven.
"""
import string

from . import config, db
from .tools import dispatch


class SiteGenError(RuntimeError):
    pass


def _load_template(template_id: str) -> string.Template:
    path = config.TEMPLATES_DIR / template_id / "index.html"
    if not path.exists():
        raise SiteGenError(f"unknown template: {template_id!r} (looked for {path})")
    return string.Template(path.read_text())


def generate_site(business_id: int, template_id: str = "template_landing_v1", site_id: int | None = None) -> dict:
    with db.get_conn() as conn:
        business = conn.execute(
            "SELECT * FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
        if not business:
            raise SiteGenError(f"unknown business_id: {business_id}")
        business = dict(business)

        site = None
        if site_id is not None:
            row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
            site = dict(row) if row else None
        if site is None:
            site = db.get_site_for_business(conn, business_id)
        if site is None:
            raise SiteGenError(f"no sites row found for business_id {business_id}")

        task_id = db.insert_task(
            conn, "website_builder", f"Generate site for {business['name']}", business_id, "normal"
        )
        db.log_event(conn, task_id, "dispatch", "deterministic site generation")

        template = _load_template(template_id)
        html = template.safe_substitute(
            business_name=business["name"],
            tagline=f"Welcome to {business['name']}.",
            contact_email=f"hello@{site['domain']}",
        )

        agent = db.get_agent(conn, "website_builder")
        if not agent:
            raise SiteGenError("website_builder agent is not registered — run `cli --init`")
        rel_path = "site/index.html"
        result = dispatch.execute_tool(
            conn, task_id, agent, business_id, "write_file",
            {"path": rel_path, "content": html},
        )

        if not result["ok"]:
            db.update_task(conn, task_id, "failed", str(result))
            raise SiteGenError(f"write_file failed: {result}")

        local_path = str((config.WORKSPACES_DIR / f"business_{business_id}" / rel_path).resolve())
        db.update_site(conn, site["id"], status="generated", local_path=local_path)
        db.update_task(conn, task_id, "done", local_path)

        return {"task_id": task_id, "site_id": site["id"], "local_path": local_path, "template_id": template_id}
