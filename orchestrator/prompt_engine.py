"""
Prompt Engine -- deterministic prompt templating and linting across this
project's actual model targets (Claude, and whatever's pulled in Ollama --
currently llama3.2 and gemma4 on this machine). DeepSeek/other Ollama
models are supported as template targets (the format differences are
model-agnostic enough to write correctly without a live instance) but
NOT verified live -- only llama3.2 and gemma4 are actually pulled here;
see `ollama list`. Treat pulling and testing against a real DeepSeek
model as the verification step for that target specifically.

Template rendering is deterministic Python -- generating a WELL-FORMED
prompt doesn't need a model's judgment. `lint_role_prompt` is the same
"deterministic where possible" philosophy as security.py/audit.py:
catches structural problems (too short, no output-format instruction) a
model reviewer would also catch, without spending a model call to find
them.
"""
import re

MODEL_PROFILES = {
    "claude": {
        "supports_system_prompt": True,
        "style": "Structured system prompt + user turn. Handles XML-ish tags, multi-step instructions, and explicit output-format contracts well.",
        "verified": "Used throughout this project for cloud escalation (config.CLOUD_MODEL) — real, live-verified calls this session.",
    },
    "llama3.2": {
        "supports_system_prompt": True,
        "style": "Local via Ollama, 3B, fast. Works best with short, direct instructions — terse over elaborate.",
        "verified": "Live-verified extensively this session (most agents' local_model).",
    },
    "gemma4": {
        "supports_system_prompt": True,
        "style": "Local via Ollama, 9.6GB, CPU-bound and slow on this machine (observed 2:24–3:26 per call — see config.OLLAMA_TIMEOUT_SECONDS). Handles longer context than llama3.2.",
        "verified": "Live-verified this session (ceo/bug_fixer/engineer's local_model).",
    },
    "deepseek": {
        "supports_system_prompt": True,
        "style": "Not pulled in this project's Ollama install — template only, format assumed compatible with standard Ollama chat templating.",
        "verified": "NOT verified live — `ollama pull deepseek-r1` (or similar) first, then test.",
    },
}


def render_prompt(target: str, role: str, task: str, constraints: list = None, output_format: str = None) -> str:
    if target not in MODEL_PROFILES:
        raise ValueError(f"unknown target '{target}' — expected one of {list(MODEL_PROFILES)}")

    lines = [f"You are {role}."]
    lines.append("")
    lines.append(task.strip())
    if constraints:
        lines.append("")
        lines.append("Constraints:")
        for c in constraints:
            lines.append(f"- {c}")
    if output_format:
        lines.append("")
        lines.append(f"Reply in exactly this format: {output_format}")

    prompt = "\n".join(lines)

    # llama3.2 is small and fast-but-literal -- keeping the prompt terser
    # measurably helps it follow instructions, per this project's own
    # established pattern (see agents/*.yaml role_prompts, all short and direct).
    if target == "llama3.2" and len(prompt) > 800:
        prompt += "\n\n(Keep your reply brief and direct.)"

    return prompt


def lint_role_prompt(role_prompt: str) -> list:
    """Structural checks only -- not a judgment on whether the prompt is
    good writing, just whether it's missing pieces every working
    agents/*.yaml role_prompt in this project actually has."""
    issues = []
    text = (role_prompt or "").strip()

    if len(text) < 40:
        issues.append("Too short to establish a real persona/role (under 40 characters).")
    if not re.search(r"(?i)\byou are\b", text):
        issues.append("No explicit persona statement (\"You are...\") — every working agent in this project opens with one.")
    if len(text) > 150 and not re.search(r"(?i)\breply\b|\bformat\b|\brespond\b|\boutput\b", text):
        issues.append("No explicit output-format instruction for a prompt this long — risks inconsistent replies.")
    if re.search(r"(?i)\bmight\b.*\bmight\b|\bmaybe\b.*\bmaybe\b", text):
        issues.append("Multiple hedge words ('might'/'maybe') — local 3B models follow direct instructions more reliably than hedged ones.")

    return issues


def optimize_prompt(conn, task_id: int, agent_id: str, role_prompt: str) -> dict:
    """Model-assisted improvement pass -- optional, not run automatically.
    Reuses bug_fixer.call_agent so this goes through the same cost-logging
    path every other model call in this project does."""
    from . import bug_fixer

    issues = lint_role_prompt(role_prompt)
    prompt = (
        "Review this AI agent system prompt for clarity and effectiveness. "
        f"Structural issues already found: {issues or 'none'}.\n\n"
        f"--- PROMPT ---\n{role_prompt}\n--- END PROMPT ---\n\n"
        "Suggest an improved version in 3-5 sentences of plain English changes, not a rewrite of the whole prompt."
    )
    suggestion = bug_fixer.call_agent(conn, task_id, agent_id, prompt)
    return {"structural_issues": issues, "suggestion": suggestion}
