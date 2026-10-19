"""
The tool catalog. Single source of truth for what a tool does, its schema,
its handler, and its risk tier -- the prompt text shown to a model and the
actual handler executed both come from here, so they can't drift apart.
"""
from . import exec_tools, file_tools

TOOL_REGISTRY = {
    "read_file": {
        "description": "Read a text file from your business workspace.",
        "schema": {"path": "string, relative to your workspace root"},
        "handler": file_tools.read_file,
        "risk_tier": "safe",
    },
    "write_file": {
        "description": "Write (or overwrite) a text file in your business workspace.",
        "schema": {"path": "string, relative to your workspace root", "content": "string"},
        "handler": file_tools.write_file,
        "risk_tier": "moderate",
    },
    "list_dir": {
        "description": "List the contents of a directory in your business workspace.",
        "schema": {"path": "string, relative to your workspace root, default '.'"},
        "handler": file_tools.list_dir,
        "risk_tier": "safe",
    },
    "run_command": {
        "description": (
            f"Run an allowlisted command ({', '.join(sorted(exec_tools.ALLOWED_COMMANDS))}) "
            "in your business workspace. Disabled unless the founder has explicitly "
            "enabled command execution."
        ),
        "schema": {"argv": "list of strings, e.g. [\"python3\", \"-c\", \"print(1)\"]"},
        "handler": lambda business_id, params: exec_tools.run_command(business_id, params["argv"]),
        "risk_tier": "dangerous",
    },
}


def describe_tools_for_agent(allowed_tools: list) -> str:
    """Prompt fragment listing exactly the tools this agent may call, and the
    exact call format the orchestrator's parser expects."""
    if not allowed_tools:
        return ""

    lines = [
        "You have access to the following tools. Use one ONLY if the task genuinely "
        "requires it -- most tasks don't. To use a tool, end your reply with a single "
        "fenced json block in exactly this form and nothing else after it:",
        '```json',
        '{"tool": "<tool_name>", "params": {...}}',
        '```',
        "If no tool is needed, just answer normally with no json block.",
        "",
        "Available tools:",
    ]
    for name in allowed_tools:
        spec = TOOL_REGISTRY.get(name)
        if not spec:
            continue
        lines.append(f"- {name}: {spec['description']} params: {spec['schema']}")
    return "\n".join(lines)
