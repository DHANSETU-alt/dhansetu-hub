"""
execute_tool() is the single choke point every file/command write in the
system goes through -- model-driven calls from routing.py and the
deterministic Website Builder path in sitegen.py both call this, never the
tool handlers directly. That's what makes the audit log complete and the
permission model actually enforced rather than advisory.
"""
import json
import time

from .. import config, db
from . import registry


def execute_tool(conn, task_id: int, agent: dict, business_id, tool_name: str, params: dict) -> dict:
    agent_id = agent["id"]
    params_json = json.dumps(params)
    started = time.monotonic()

    def _deny(reason: str) -> dict:
        db.log_tool_call(
            conn, task_id, agent_id, business_id, tool_name, params_json,
            decision="denied", denial_reason=reason,
        )
        return {"ok": False, "denied": True, "reason": reason}

    spec = registry.TOOL_REGISTRY.get(tool_name)
    if not spec:
        return _deny(f"unknown tool: {tool_name!r}")

    allowed_tools = json.loads(agent.get("allowed_tools") or "[]")
    if tool_name not in allowed_tools:
        return _deny(f"agent '{agent_id}' is not permitted to use '{tool_name}'")

    if spec["risk_tier"] == "dangerous" and not config.ALLOW_EXEC:
        return _deny(
            f"'{tool_name}' is a dangerous-tier tool and SHAKTHI_ALLOW_EXEC is not set"
        )

    if config.TOOLS_DRY_RUN:
        db.log_tool_call(
            conn, task_id, agent_id, business_id, tool_name, params_json,
            decision="dry_run", output_summary="not executed (dry-run mode)",
        )
        return {"ok": True, "dry_run": True}

    try:
        result = spec["handler"](business_id, params)
        duration_ms = int((time.monotonic() - started) * 1000)
        summary = json.dumps(result)[:2000]
        db.log_tool_call(
            conn, task_id, agent_id, business_id, tool_name, params_json,
            decision="allowed", output_summary=summary, duration_ms=duration_ms,
        )
        return {"ok": True, "result": result}
    except Exception as e:
        duration_ms = int((time.monotonic() - started) * 1000)
        db.log_tool_call(
            conn, task_id, agent_id, business_id, tool_name, params_json,
            decision="allowed", output_summary=f"ERROR: {e}", duration_ms=duration_ms,
        )
        return {"ok": False, "error": str(e)}
