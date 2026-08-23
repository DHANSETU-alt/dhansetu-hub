"""
Lenient parser for the model's tool-call convention (see registry.py's
describe_tools_for_agent for the format shown to the model). Returns None
on no match or a parse failure -- that's the common case, a plain-text
answer with no tool call, and it must never raise for it.
"""
import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_tool_call(text: str):
    match = None
    for match in _FENCE_RE.finditer(text):
        pass  # take the last fenced block, in case the model reasons before it
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict) or "tool" not in data:
        return None

    return {"tool": data["tool"], "params": data.get("params", {})}
