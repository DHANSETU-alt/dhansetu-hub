"""
Task routing — Phase 8 of the architecture doc, as code.

classify -> (critical? straight to cloud) -> execute on local model ->
validate via the QA agent -> pass? done : escalate to cloud once -> log cost
either way.
"""
import json

from . import config, db, model_gateway
from .tools import dispatch, parsing
from .tools import registry as tool_registry

CRITICAL_KEYWORDS = (
    "refund", "cancel subscription", "contract", "custom pricing", "legal",
    "lawsuit", "production database", "delete all", "credentials", "secret key",
)


def classify_risk(goal: str) -> str:
    lowered = goal.lower()
    if any(kw in lowered for kw in CRITICAL_KEYWORDS):
        return "critical"
    return "normal"


def run_task(agent_id: str, goal: str, business_id: int | None = None, force_risk: str | None = None) -> dict:
    with db.get_conn() as conn:
        agent = db.get_agent(conn, agent_id)
        if not agent:
            raise ValueError(f"Unknown agent '{agent_id}'. Run `python -m orchestrator.cli --list-agents`.")

        risk = force_risk or classify_risk(goal)
        task_id = db.insert_task(conn, agent_id, goal, business_id, risk)
        db.log_event(conn, task_id, "dispatch", json.dumps({"risk": risk, "agent": agent_id}))

        cross_tenant = agent["allowed_scope"] == "cross_tenant"
        memories = db.recent_memory(conn, business_id, cross_tenant=cross_tenant)
        memory_context = "\n".join(f"- {m['content']}" for m in memories) or "(none yet)"
        user_prompt = f"Relevant memory:\n{memory_context}\n\nTask:\n{goal}"

        allowed_tools = json.loads(agent.get("allowed_tools") or "[]")
        tools_prompt = tool_registry.describe_tools_for_agent(allowed_tools)
        if tools_prompt:
            user_prompt = f"{user_prompt}\n\n{tools_prompt}"

        if risk == "critical":
            output, status = _try_cloud(conn, task_id, agent, user_prompt)
            output = _maybe_execute_tool(conn, task_id, agent, business_id, output)
            db.update_task(conn, task_id, status, output)
            _write_memory(conn, task_id, agent, goal, output, business_id)
            return {"task_id": task_id, "status": status, "output": output, "escalated": True}

        text, tin, tout = model_gateway.call_local(agent["local_model"], agent["role_prompt"], user_prompt)
        db.log_cost(conn, task_id, agent_id, agent["local_model"], "ollama", tin, tout, 0.0)

        if agent_id in ("qa", "memory"):
            db.update_task(conn, task_id, "done", text)
            _write_memory(conn, task_id, agent, goal, text, business_id)
            return {"task_id": task_id, "status": "done", "output": text, "escalated": False}

        # QA validates the proposal (the raw text, tool-call block included)
        # BEFORE anything executes -- a QA-rejected proposal never runs.
        passed, qa_note = _validate(conn, task_id, text, goal)
        db.log_event(conn, task_id, "validate_pass" if passed else "validate_fail", qa_note)

        if passed:
            text = _maybe_execute_tool(conn, task_id, agent, business_id, text)
            db.update_task(conn, task_id, "done", text)
            _write_memory(conn, task_id, agent, goal, text, business_id)
            return {"task_id": task_id, "status": "done", "output": text, "escalated": False}

        output, status = _try_cloud(conn, task_id, agent, user_prompt)
        output = _maybe_execute_tool(conn, task_id, agent, business_id, output)
        db.update_task(conn, task_id, status, output)
        _write_memory(conn, task_id, agent, goal, output, business_id)
        return {"task_id": task_id, "status": status, "output": output, "escalated": True}


def _validate(conn, task_id: int, output: str, goal: str) -> tuple[bool, str]:
    qa_agent = db.get_agent(conn, "qa")
    if not qa_agent:
        return True, "no QA agent registered — validation skipped"
    prompt = f"Task goal: {goal}\n\nAgent output to review:\n{output}"
    text, tin, tout = model_gateway.call_local(qa_agent["local_model"], qa_agent["role_prompt"], prompt)
    db.log_cost(conn, task_id, "qa", qa_agent["local_model"], "ollama", tin, tout, 0.0)
    passed = text.strip().upper().startswith("PASS")
    return passed, text


def _try_cloud(conn, task_id: int, agent: dict, user_prompt: str) -> tuple[str, str]:
    db.log_event(conn, task_id, "escalate", "routing to Claude")
    try:
        text, tin, tout = model_gateway.call_cloud(agent["role_prompt"], user_prompt)
        cost = model_gateway.estimate_cloud_cost(tin, tout)
        db.log_cost(conn, task_id, agent["id"], config.CLOUD_MODEL, "claude", tin, tout, cost)
        return text, "done"
    except model_gateway.ModelError as e:
        db.log_event(conn, task_id, "escalation_unavailable", str(e))
        return f"[escalation unavailable, returning best local effort: {e}]", "failed"


def _maybe_execute_tool(conn, task_id: int, agent: dict, business_id, text: str) -> str:
    """At most one tool call per task -- not an open-ended agentic loop. If
    the model's reply contains a tool-call block, execute it through the
    single dispatch.execute_tool() choke point (permission + audit) and
    append the result. No block found -> text returned unchanged."""
    call = parsing.parse_tool_call(text)
    if not call:
        return text

    result = dispatch.execute_tool(conn, task_id, agent, business_id, call["tool"], call["params"])
    return f"{text}\n\n---\nTool call: {call['tool']}\nResult: {json.dumps(result)}"


def _write_memory(conn, task_id: int, agent: dict, goal: str, output: str, business_id: int | None):
    mem_agent = db.get_agent(conn, "memory")
    if not mem_agent or agent["id"] == "memory":
        return
    prompt = f"Task: {goal}\n\nResult:\n{output}"
    text, tin, tout = model_gateway.call_local(mem_agent["local_model"], mem_agent["role_prompt"], prompt)
    db.log_cost(conn, task_id, "memory", mem_agent["local_model"], "ollama", tin, tout, 0.0)
    db.insert_memory(conn, "project", text, business_id, tags=agent["id"])
