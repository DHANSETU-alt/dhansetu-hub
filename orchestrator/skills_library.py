"""
Reference library over the externally-installed agent-skills bundle
(~/.agents/skills/, from addyosmani/agent-skills -- 25 skills added
2026-09-13 via `npx skills add`). These are generic software-engineering
process skills (TDD, code review, git workflow, security hardening, etc.),
authored for Claude/agent harnesses that read a SKILL.md file directly --
not something Shakthi_OS's own local-model agents (routing.run_task,
Ollama-backed) previously had any way to draw on.

This module does not rewrite any of the 58 agents' role_prompts to claim
they "know" all 25 skills -- most are irrelevant to most agents (customer
support and finance agents have no use for git-workflow-and-versioning).
Instead it exposes the real content on demand, so a caller of
routing.run_task can opt a specific task into a specific skill's guidance
via the `skill_hint` parameter, only when it's actually relevant.
"""
import os
from pathlib import Path

SKILLS_DIR = Path(os.environ.get("SHAKTHI_SKILLS_DIR", os.path.expanduser("~/.agents/skills")))


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a SKILL.md's `---` frontmatter from its markdown body.
    Minimal, dependency-free -- only reads the two keys this module needs
    (name, description), not a full YAML parser."""
    meta: dict[str, str] = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    frontmatter, body = text[3:end].strip(), text[end + 4:].lstrip("\n")
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def list_skills() -> list[dict]:
    """Every installed skill's name + one-line description, sorted by
    name. Returns [] (not an error) if the skills directory doesn't
    exist on this machine -- an agent without it just has none to offer."""
    if not SKILLS_DIR.is_dir():
        return []
    out = []
    for entry in sorted(SKILLS_DIR.iterdir()):
        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            continue
        meta, _ = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        out.append({"name": meta.get("name", entry.name), "description": meta.get("description", "")})
    return out


def load_skill(name: str) -> str | None:
    """Full markdown body (frontmatter stripped) of one skill by its
    directory name, or None if it isn't installed."""
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if not skill_file.is_file():
        return None
    _, body = _parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    return body.strip()
