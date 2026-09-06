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

# Real 4-tier classification, added for the Founder Command Center's
# priority display (Task 13). CRITICAL_KEYWORDS and the "critical" value
# are completely unchanged -- the cloud-escalation gate in run_task()
# below still checks `risk == "critical"` exactly as before, so this
# extension cannot change which tasks escalate to cloud. HIGH/LOW are
# purely additive classification bands for goals that don't hit a
# critical keyword; deterministic keyword matching only, same reasoning
# as CRITICAL_KEYWORDS itself (a 3B local model's risk judgment isn't a
# reliable gate for this).

# Multi-word phrases, not bare single words -- a real test
# (test_founder_examples_are_not_critical) already encodes that generic
# verbs like "check"/"review"/"security" appear constantly in normal
# read-only status commands ("security audit start karo" must stay
# "normal", not get pulled into "high" just because it contains
# "security"). Same style CRITICAL_KEYWORDS already uses for exactly
# this reason -- specific phrases, not words common enough to false-positive.
HIGH_KEYWORDS = (
    "deploy to production", "go live", "launch campaign", "security incident",
    "customer data breach", "site outage", "publish live", "production outage",
)
LOW_KEYWORDS = ("just a draft", "rough idea", "quick brainstorm", "just exploring")

# Agents whose whole job is faithful, real-time handling of the exact
# message they're given -- injecting unrelated "Relevant memory" context
# does these agents active harm, not just no benefit. Found live: asked to
# refine a message with no revenue figure in it, PA Angella stated a stale
# number from an unrelated earlier task as if it were the real answer.
# Tried fixing this with role_prompt wording first -- a real, honest
# result: the 3B local model partially followed it (stopped asserting the
# stale number as fact) but then started echoing the prompt's own
# "Relevant memory:" section labels back verbatim, which is worse
# formatting, not better. A deterministic fix (don't inject it at all) is
# more reliable than continuing to steer a 3B model with more wording.
NO_MEMORY_CONTEXT = (
    "pa_angella",
    # Same bug, found live a second time: analyzing a real bakery's intake
    # (Sunrise Bakery), business_analyst's "operational" and "sales"
    # findings cited "Dhansetu launch," "45 tasks logged," and "Manager's
    # instructions" -- none of which have anything to do with a bakery.
    # This agent's whole job is judging THIS business's intake, not
    # reasoning from unrelated prior tasks.
    "business_analyst",
    # Third confirmed instance, found live a third time: asked to write a
    # real cold email for blackboxOps_OS, marketing cited "manual tracking
    # of custom orders" and "no online presence" -- real details, but from
    # the Sunrise Bakery test intake's own memory entry, not the actual
    # brief it was given. The `business_discoveries` row was deleted; the
    # memory entry _write_memory() created from analyzing it wasn't (no
    # cascade), and outlived the data it summarized. Given the pattern is
    # now 3-for-3 on agents whose job is "handle only what you were given,"
    # applying it broadly here rather than waiting to find it a 4th time --
    # every one below either has an explicit role_prompt rule to use only
    # the given input (sales, marketing, knowledge) or handles one specific
    # item per call where unrelated history is actively misleading, not
    # just unhelpful (customer_success: one ticket; the 4 Dhansetu
    # specialists: one course/content item each).
    "marketing",
    "sales",
    "customer_success",
    "knowledge",
    "course_writer",
    "prompt_writer",
    "reel_scripter",
    "content_scheduler",
)


def classify_risk(goal: str) -> str:
    lowered = goal.lower()
    if any(kw in lowered for kw in CRITICAL_KEYWORDS):
        return "critical"
    if any(kw in lowered for kw in HIGH_KEYWORDS):
        return "high"
    if any(kw in lowered for kw in LOW_KEYWORDS):
        return "low"
    return "normal"


def run_task(agent_id: str, goal: str, business_id: int | None = None, force_risk: str | None = None) -> dict:
    with db.get_conn() as conn:
        agent = db.get_agent(conn, agent_id)
        if not agent:
            raise ValueError(f"Unknown agent '{agent_id}'. Run `python -m orchestrator.cli --list-agents`.")

        risk = force_risk or classify_risk(goal)
        task_id = db.insert_task(conn, agent_id, goal, business_id, risk)
        db.log_event(conn, task_id, "dispatch", json.dumps({"risk": risk, "agent": agent_id}))

        if agent_id in NO_MEMORY_CONTEXT:
            user_prompt = goal
        else:
            cross_tenant = agent["allowed_scope"] == "cross_tenant"
            memories = db.recent_memory(conn, business_id, cross_tenant=cross_tenant)
            memory_context = "\n".join(f"- {m['content']}" for m in memories) or "(none yet)"
            user_prompt = f"Relevant memory:\n{memory_context}\n\nTask:\n{goal}"

        allowed_tools = json.loads(agent.get("allowed_tools") or "[]")
        tools_prompt = tool_registry.describe_tools_for_agent(allowed_tools)
        if tools_prompt:
            user_prompt = f"{user_prompt}\n\n{tools_prompt}"

        if risk == "critical":
            # Found live: with no ANTHROPIC_API_KEY set, every critical-risk
            # decision (cancel subscription, delete records, launch
            # readiness...) returned a bare "[escalation unavailable]"
            # string and status='failed' -- CEO rendered NO judgment call
            # at all for the highest-stakes goals specifically. Same fix
            # as the normal-risk QA-fail path below: fall back to a real
            # local-model decision, lazily -- only generated if cloud
            # actually fails, so the common (cloud-available) case pays no
            # extra local-model cost.
            output, status = _try_cloud(
                conn, task_id, agent, user_prompt,
                local_fallback_fn=lambda: model_gateway.call_local(
                    agent["local_model"], agent["role_prompt"], user_prompt
                ),
            )
            output = _maybe_execute_tool(conn, task_id, agent, business_id, output)
            db.update_task(conn, task_id, status, output)
            _write_memory(conn, task_id, agent, goal, output, business_id)
            return {"task_id": task_id, "status": status, "output": output, "escalated": True}

        text, tin, tout = model_gateway.call_local(agent["local_model"], agent["role_prompt"], user_prompt)
        db.log_cost(conn, task_id, agent_id, agent["local_model"], "ollama", tin, tout, 0.0)

        # qa/memory never get QA'd (they'd be reviewing themselves). ceo
        # is exempt too -- found live: QA's role is judging a PROPOSED
        # ACTION for unmet requirements/bugs/unsafe behavior, and it was
        # rejecting CEO's own legitimate "revise" decisions as if
        # declining to approve were itself a bug. A decision task's job
        # is to render SOME reasoned judgment; approve and revise are
        # both valid outcomes, and CEO reviewing CEO's own decision with
        # a second local model isn't the kind of check QA is built for.
        if agent_id in ("qa", "memory", "ceo"):
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

        output, status = _try_cloud(conn, task_id, agent, user_prompt, local_fallback_text=text)
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


def _try_cloud(conn, task_id: int, agent: dict, user_prompt: str, local_fallback_text: str = None,
                local_fallback_fn=None) -> tuple[str, str]:
    db.log_event(conn, task_id, "escalate", "routing to Claude")
    try:
        text, tin, tout = model_gateway.call_cloud(agent["role_prompt"], user_prompt)
        cost = model_gateway.estimate_cloud_cost(tin, tout)
        db.log_cost(conn, task_id, agent["id"], config.CLOUD_MODEL, "claude", tin, tout, cost)
        return text, "done"
    except model_gateway.ModelError as e:
        db.log_event(conn, task_id, "escalation_unavailable", str(e))
        # Found live: this used to discard the local model's actual QA-
        # failed output and replace it with this message alone -- for
        # CEO's decision tasks specifically, that meant a real, parseable
        # decision (with real reasoning) was silently thrown away and
        # replaced with an unparseable string, turning "QA was too
        # strict" into "the decision is gone." Fall back to the real
        # local output when we have one; only use the bare message when
        # there's truly nothing to fall back to.
        if local_fallback_text is None and local_fallback_fn is not None:
            local_fallback_text, tin, tout = local_fallback_fn()
            db.log_cost(conn, task_id, agent["id"], agent["local_model"], "ollama", tin, tout, 0.0)
        if local_fallback_text:
            return (f"{local_fallback_text}\n\n[Note: this is the local model's own output -- "
                    f"cloud escalation was attempted and unavailable: {e}]", "done_local_fallback")
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
