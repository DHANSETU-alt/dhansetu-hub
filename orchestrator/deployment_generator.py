"""
SHAKTHI WEBSITE BUILDER — deployment packaging.

Packages a built project's site directory into a downloadable .zip plus a
DEPLOY.md with real, concrete instructions for static hosting. Honest
scope: there is no live hosting integration anywhere in this system (no
Vercel/Netlify/Caddy API credentials configured) -- this produces a
ready-to-upload bundle, not an actual deployment. That's a real, distinct
next step (a DevOps-layer capability this system doesn't have yet), not
something to fake here.
"""
import zipfile
from pathlib import Path

from . import db

DEPLOY_INSTRUCTIONS = """# Deployment Instructions

This is a static site (a single index.html, no build step, no server-side
code) -- it can be deployed to any static host. No live deployment was
performed; this package is ready for you to upload.

## Option 1: Vercel / Netlify (drag-and-drop)
Unzip this package and drag the folder onto the Vercel or Netlify web
dashboard's deploy area. Done in under a minute, free tier is enough.

## Option 2: Any static host / your own server
Copy index.html (and this file) to your web server's document root, or
any S3-compatible bucket configured for static website hosting.

## Option 3: GitHub Pages
Push this folder to a repo, enable Pages in repo settings, point it at
this branch.

No environment variables, no build command, no server required -- it's
one HTML file with inline CSS.
"""


def create_package(project_id: int) -> dict:
    with db.get_conn() as conn:
        project = db.get_website_project(conn, project_id)
        if not project:
            raise ValueError(f"no such project: {project_id}")
        if project["status"] != "security_passed":
            raise ValueError(f"project {project_id} has not passed security review (status={project['status']}) — cannot package")
        site = conn.execute("SELECT * FROM sites WHERE id = ?", (project["site_id"],)).fetchone()
        site = dict(site)

    source_path = Path(site["local_path"])
    if not source_path.exists():
        raise ValueError(f"generated file not found: {source_path}")

    package_dir = source_path.parent / "package"
    package_dir.mkdir(exist_ok=True)
    zip_path = package_dir / f"project_{project_id}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(source_path, arcname="index.html")
        zf.writestr("DEPLOY.md", DEPLOY_INSTRUCTIONS)

    with db.get_conn() as conn:
        db.update_website_project(conn, project_id, status="packaged", deployment_package_path=str(zip_path))

    return {"project_id": project_id, "package_path": str(zip_path), "size_bytes": zip_path.stat().st_size}
