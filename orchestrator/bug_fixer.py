"""
Bug Fixer workflow — Phase 0.4.

Pipeline: scan (real logs) -> analyze (bug_fixer agent) -> propose_patch
(engineer agent, writes to staging only) -> qa_review (qa agent) ->
security_review (security agent: deterministic checks + summary) ->
ceo_review (ceo agent) -> [human --confirm] apply_patch (backs up the
original, then overwrites) -> run_tests -> verified / regressed.

Every model call here goes through a real task row, same cost_ledger /
task_events integration as any other agent call in this system -- no
parallel cost-tracking mechanism invented for this one workflow.

apply_patch() is the one function in this module that touches the live
codebase, and it refuses to run without confirm=True and a prior
'ceo_approved' status -- see bugfix_tools.py for why that boundary exists.
"""
import difflib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from . import bugfix_tools as bft
from . import config, db, model_gateway
from . import security as security_mod

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

# P0-P4, not "critical/high/medium/low" -- an explicit incident-management-
# style scale, ordered worst-first so SEVERITY_ORDER[x] < SEVERITY_ORDER[y]
# means x is more severe than y.
SEVERITY_LABELS = {
    "P0": "Critical — production down, security breach, or data loss",
    "P1": "High — major feature broken, no workaround",
    "P2": "Medium — feature degraded, workaround exists",
    "P3": "Low — minor issue, cosmetic-adjacent",
    "P4": "Trivial — cosmetic, typo, nice-to-have",
}
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}

SENSITIVE_FILES = ("tools/paths.py", "tools/exec_tools.py", "tools/dispatch.py",
                    "bugfix_tools.py", "sheets.py", "model_gateway.py", "config.py")

DANGEROUS_PATCH_PATTERNS = {
    "eval_call": re.compile(r"\beval\s*\("),
    "exec_call": re.compile(r"\bexec\s*\("),
    "os_system": re.compile(r"\bos\.system\s*\("),
    "shell_true": re.compile(r"shell\s*=\s*True"),
}


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


def new_pipeline_task(conn, goal: str) -> int:
    return db.insert_task(conn, "bug_fixer", goal, business_id=None, risk_level="normal")


def call_agent(conn, task_id: int, agent_id: str, user_prompt: str) -> str:
    agent = db.get_agent(conn, agent_id)
    if not agent:
        raise RuntimeError(f"agent '{agent_id}' not registered — run `cli --init`")
    text, tin, tout = model_gateway.call_local(agent["local_model"], agent["role_prompt"], user_prompt)
    db.log_cost(conn, task_id, agent_id, agent["local_model"], "ollama", tin, tout, 0.0)
    return text


# --- Detection --------------------------------------------------------------

def scan_for_bugs() -> list:
    """Real log sources: failed tasks and untriaged error_log rows. Does
    NOT re-surface anything already tracked as a bug."""
    candidates = []
    with db.get_conn() as conn:
        tracked = db.list_bugs(conn, limit=1000)
        seen_tasks = {b["related_task_id"] for b in tracked if b["related_task_id"]}
        seen_errors = {b["related_error_id"] for b in tracked if b["related_error_id"]}

        for t in db.recent_tasks(conn, limit=200):
            if t["status"] == "failed" and t["id"] not in seen_tasks:
                candidates.append({"source": "task_failure", "related_task_id": t["id"],
                                    "title": f"Task #{t['id']} failed (agent: {t['agent_id']})"})

        for e in db.untriaged_errors(conn, limit=100):
            if e["id"] not in seen_errors:
                candidates.append({"source": "error_log", "related_error_id": e["id"],
                                    "title": f"{e['source']} error: {e['message'][:80]}"})
    return candidates


def _describe_candidate(conn, candidate: dict) -> str:
    if candidate["source"] == "task_failure":
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (candidate["related_task_id"],)).fetchone()
        task = dict(task) if task else {}
        return f"Goal: {task.get('goal')}\nAgent: {task.get('agent_id')}\nResult: {task.get('result')}"
    if candidate["source"] == "error_log":
        row = conn.execute("SELECT * FROM error_log WHERE id = ?", (candidate["related_error_id"],)).fetchone()
        row = dict(row) if row else {}
        return f"Source: {row.get('source')}\nModule: {row.get('module')}\nMessage: {row.get('message')}\nTraceback:\n{row.get('traceback')}"
    return candidate.get("title", "")


def report_bug(title: str, description: str, severity: str = "P2") -> int:
    """Manual entry point -- a founder or another agent filing a bug
    directly, rather than it coming from an automated scan."""
    with db.get_conn() as conn:
        bug_id = db.insert_bug(conn, title, description, severity, source="manual")
        db.log_bug_event(conn, bug_id, "detected", "manually reported")
    return bug_id


# --- Analysis (bug_fixer agent) ---------------------------------------------

def _run_analysis(bug_id: int, description: str) -> dict:
    """Shared by create_and_analyze() (scan candidates) and analyze_bug()
    (manually-reported bugs, or re-analyzing one) -- one place that calls
    the bug_fixer agent and writes the 7 report fields, so the two entry
    points can't drift into different prompts or update logic."""
    with db.get_conn() as conn:
        task_id = new_pipeline_task(conn, f"Analyze bug #{bug_id}")
        prompt = (
            f"Bug report:\n{description}\n\n"
            "You are a Staff Software Engineer analyzing this bug. Severity is one of:\n"
            + "\n".join(f"  {k}: {v}" for k, v in SEVERITY_LABELS.items()) + "\n\n"
            "Reply with ONLY a single fenced json block, nothing else:\n"
            '```json\n{"severity": "P0|P1|P2|P3|P4", "file_path": "relative/path.py", '
            '"function_name": "...", "line_number": 0, "module_name": "...", '
            '"root_cause": "one or two sentences", "fix_recommendation": "one or two sentences", '
            '"confidence": 0}\n```\n'
            "confidence is 0-100. line_number is your best estimate from the evidence given, "
            "or null if you can't tell. If you cannot determine any field, use null."
        )
        text = call_agent(conn, task_id, "bug_fixer", prompt)
        parsed = _parse_json_block(text)

        if parsed is None:
            db.update_task(conn, task_id, "failed", text)
            db.log_bug_event(conn, bug_id, "analyzed", "could not parse analysis — left open for manual triage")
            return {"bug_id": bug_id, "parsed": False, "raw": text}

        severity = parsed.get("severity") or "P2"
        if severity not in SEVERITY_LABELS:
            severity = "P2"  # a model hallucinating "high" instead of "P1" shouldn't crash the update

        line_number = parsed.get("line_number")
        try:
            line_number = int(line_number) if line_number is not None else None
        except (TypeError, ValueError):
            line_number = None

        db.update_bug(
            conn, bug_id, status="analyzing", severity=severity,
            file_path=parsed.get("file_path"), function_name=parsed.get("function_name"),
            line_number=line_number, module_name=parsed.get("module_name"),
            root_cause=parsed.get("root_cause"), fix_recommendation=parsed.get("fix_recommendation"),
            confidence=int(parsed.get("confidence") or 0),
        )
        db.log_bug_event(conn, bug_id, "analyzed", text)
        db.update_task(conn, task_id, "done", text)

        recurrence = _check_recurrence(bug_id, parsed.get("file_path"), parsed.get("function_name"))
        result = {"bug_id": bug_id, "parsed": True, "severity": severity, "line_number": line_number, **parsed}
        if recurrence:
            result["recurrence_of"] = recurrence
        return result


def _check_recurrence(bug_id: int, file_path, function_name) -> int:
    """If an earlier, non-duplicate bug exists at the same (file, function),
    this bug is a recurrence, not a fresh independent one: link it, bump
    the original's occurrence_count, close this one, and log 'recurred' on
    the original. Returns the original bug's id, or None if this is fresh."""
    if not file_path or not function_name:
        return None
    with db.get_conn() as conn:
        original = db.find_bug_by_signature(conn, file_path, function_name, exclude_bug_id=bug_id)
        if not original:
            return None
        db.increment_occurrence(conn, original["id"])
        db.update_bug(conn, bug_id, status="closed", duplicate_of=original["id"])
        db.log_bug_event(conn, original["id"], "recurred", f"recurrence detected via bug #{bug_id}")
        db.log_bug_event(conn, bug_id, "detected", f"closed as a recurrence of bug #{original['id']}")
        return original["id"]


def create_and_analyze(candidate: dict) -> dict:
    """For scan_for_bugs() candidates -- creates the bug row, then analyzes it."""
    with db.get_conn() as conn:
        description = _describe_candidate(conn, candidate)
        bug_id = db.insert_bug(
            conn, candidate["title"], description, severity="medium", source=candidate["source"],
            related_task_id=candidate.get("related_task_id"), related_error_id=candidate.get("related_error_id"),
        )
        if candidate.get("related_error_id"):
            db.mark_error_triaged(conn, candidate["related_error_id"], bug_id)
        db.log_bug_event(conn, bug_id, "detected", json.dumps(candidate))
    return _run_analysis(bug_id, description)


def analyze_bug(bug_id: int) -> dict:
    """For an already-existing bug row -- a manual report_bug(), or
    re-running analysis. Uses the bug's own title/description as the
    report text handed to the bug_fixer agent."""
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            raise ValueError(f"no such bug: {bug_id}")
        description = f"{bug['title']}\n\n{bug['description'] or ''}"
    return _run_analysis(bug_id, description)


# --- Patch proposal (engineer agent) ----------------------------------------

def propose_patch(bug_id: int) -> dict:
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            raise ValueError(f"no such bug: {bug_id}")

        source_excerpt = "(no file_path on this bug yet — run analysis first)"
        if bug["file_path"]:
            try:
                source_excerpt = bft.read_source_file(bug["file_path"])
            except Exception as e:
                source_excerpt = f"(could not read {bug['file_path']}: {e})"

        task_id = new_pipeline_task(conn, f"Propose patch for bug #{bug_id}")
        prompt = (
            f"Bug #{bug_id}: {bug['title']}\nRoot cause: {bug['root_cause']}\n"
            f"Fix recommendation: {bug['fix_recommendation']}\nFile: {bug['file_path']}\n\n"
            f"Current file content:\n{source_excerpt}\n\n"
            "Write the corrected, COMPLETE file content implementing the fix. "
            "No commentary, no markdown fences — just the raw file content."
        )
        patched_content = call_agent(conn, task_id, "engineer", prompt)
        db.update_task(conn, task_id, "done", "(patch proposed — see staged file, not applied)")

        staged_name = (bug["file_path"] or "proposed_fix.txt").replace("/", "__")
        staged_path = bft.write_staged_patch(bug_id, staged_name, patched_content)

        diff_text = "".join(difflib.unified_diff(
            source_excerpt.splitlines(keepends=True),
            patched_content.splitlines(keepends=True),
            fromfile=f"a/{bug['file_path']}", tofile=f"b/{bug['file_path']}",
        ))
        diff_path = None
        if diff_text:
            diff_staged = bft.write_staged_patch(bug_id, staged_name + ".diff", diff_text)
            diff_path = str(diff_staged)

        patch_id = db.insert_patch(conn, bug_id, target_file=bug["file_path"] or "",
                                    full_file_path=str(staged_path), diff_path=diff_path)

        db.update_bug(conn, bug_id, status="patch_proposed", patch_path=str(staged_path), current_patch_id=patch_id)
        db.log_bug_event(conn, bug_id, "patch_proposed", json.dumps({"patch_id": patch_id, "diff_path": diff_path}))
        return {"bug_id": bug_id, "patch_id": patch_id, "patch_path": str(staged_path), "diff_path": diff_path}


# --- QA review ---------------------------------------------------------------

def qa_review(bug_id: int) -> dict:
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug or not bug["patch_path"]:
            raise ValueError("bug has no proposed patch yet — run propose_patch first")
        patch_content = Path(bug["patch_path"]).read_text()

        task_id = new_pipeline_task(conn, f"QA review patch for bug #{bug_id}")
        prompt = (
            f"Bug: {bug['title']}\nRoot cause: {bug['root_cause']}\n\n"
            f"Proposed fixed file content:\n{patch_content}\n\n"
            "Does this plausibly fix the described root cause without obviously breaking "
            "anything? Reply PASS or FAIL on the first line, then a short reason."
        )
        text = call_agent(conn, task_id, "qa", prompt)
        passed = text.strip().upper().startswith("PASS")
        db.update_task(conn, task_id, "done", text)
        db.log_bug_event(conn, bug_id, "qa_reviewed", text)
        if not passed:
            db.update_bug(conn, bug_id, status="open")
        return {"bug_id": bug_id, "passed": passed, "note": text}


# --- Security review (deterministic + security agent summary) --------------

def security_review(bug_id: int) -> dict:
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug or not bug["patch_path"]:
            raise ValueError("bug has no proposed patch yet — run propose_patch first")
        patch_content = Path(bug["patch_path"]).read_text()

        findings = []
        for name, pattern in security_mod.SECRET_PATTERNS.items():
            if pattern.search(patch_content):
                findings.append({"check": name, "severity": "high", "kind": "secret"})
        for name, pattern in DANGEROUS_PATCH_PATTERNS.items():
            if pattern.search(patch_content):
                findings.append({"check": name, "severity": "high", "kind": "dangerous_pattern"})
        if bug["file_path"] and any(s in bug["file_path"] for s in SENSITIVE_FILES):
            findings.append({"check": "touches_sensitive_module", "severity": "medium",
                              "kind": "scope", "file": bug["file_path"]})

        task_id = new_pipeline_task(conn, f"Security review patch for bug #{bug_id}")
        prompt = (
            f"Deterministic findings for this proposed patch: {json.dumps(findings) if findings else 'none'}\n\n"
            "In 2-3 plain sentences, summarize what this means for the founder and whether "
            "this patch should proceed to CEO review as-is."
        )
        summary = call_agent(conn, task_id, "security", prompt)
        db.update_task(conn, task_id, "done", summary)

        db.log_bug_event(conn, bug_id, "security_reviewed", json.dumps({"findings": findings, "summary": summary}))
        blocked = any(f["severity"] == "high" for f in findings)
        if blocked:
            db.update_bug(conn, bug_id, status="open")
        return {"bug_id": bug_id, "findings": findings, "summary": summary, "blocked": blocked}


# --- CEO review ---------------------------------------------------------------

def ceo_review(bug_id: int) -> dict:
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            raise ValueError(f"no such bug: {bug_id}")

        task_id = new_pipeline_task(conn, f"CEO review fix for bug #{bug_id}")
        prompt = (
            f"Bug #{bug_id} [{bug['severity']}]: {bug['title']}\n"
            f"Root cause: {bug['root_cause']}\nFix: {bug['fix_recommendation']}\n"
            f"File: {bug['file_path']}  Confidence: {bug['confidence']}\n\n"
            "Should this fix be applied? Reply with ONLY a fenced json block:\n"
            '```json\n{"status": "approved|rejected|revise", "priority_score": 0, '
            '"risk_score": 0, "business_impact_score": 0, "reason": "..."}\n```'
        )
        text = call_agent(conn, task_id, "ceo", prompt)
        parsed = _parse_json_block(text)
        db.update_task(conn, task_id, "done", text)

        if parsed is None:
            db.update_bug(conn, bug_id, status="open")
            db.log_bug_event(conn, bug_id, "ceo_rejected", "unparseable CEO output — treated as not approved")
            return {"bug_id": bug_id, "approved": False, "raw": text}

        db.insert_decision(conn, task_id, None, bug["title"], parsed.get("status", "revise"),
                            parsed.get("priority_score"), parsed.get("risk_score"),
                            parsed.get("business_impact_score"), parsed.get("reason", ""))

        approved = parsed.get("status") == "approved"
        db.update_bug(conn, bug_id, status="ceo_approved" if approved else "open")
        db.log_bug_event(conn, bug_id, "ceo_approved" if approved else "ceo_rejected", text)
        return {"bug_id": bug_id, "approved": approved, **parsed}


def run_full_review_pipeline(bug_id: int) -> dict:
    propose_patch(bug_id)
    qa_result = qa_review(bug_id)
    if not qa_result["passed"]:
        return {"bug_id": bug_id, "stage": "qa", "approved": False, "detail": qa_result}
    sec_result = security_review(bug_id)
    if sec_result["blocked"]:
        return {"bug_id": bug_id, "stage": "security", "approved": False, "detail": sec_result}
    ceo_result = ceo_review(bug_id)
    return {"bug_id": bug_id, "stage": "ceo", "approved": ceo_result["approved"], "detail": ceo_result}


# --- Apply / test / verify — the only functions that touch live code -------

def apply_patch(bug_id: int, confirm: bool = False) -> dict:
    if not confirm:
        raise ValueError("apply_patch requires confirm=True — this overwrites a real source file")
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            raise ValueError(f"no such bug: {bug_id}")
        if bug["status"] != "ceo_approved":
            raise ValueError(f"bug #{bug_id} is not CEO-approved (status={bug['status']}) — cannot apply")
        if not bug["patch_path"] or not bug["file_path"]:
            raise ValueError("bug has no staged patch or target file")

        target = bft.resolve_in_codebase(bug["file_path"])
        backup_path = bft.staging_dir_for(bug_id) / (target.name + ".backup")
        backup_path.write_text(target.read_text())

        patch_content = Path(bug["patch_path"]).read_text()
        target.write_text(patch_content)

        applied_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        db.update_bug(conn, bug_id, status="fix_applied", applied_at=applied_at)
        if bug["current_patch_id"]:
            db.mark_patch_applied(conn, bug["current_patch_id"])
        db.log_bug_event(conn, bug_id, "patch_applied", f"backup at {backup_path}")

    # Correction Bot runs automatically after every applied patch -- a
    # review-only pass on the applied content, never reapplied or gated on;
    # a correction-bot failure must never undo an already-approved,
    # already-applied fix.
    from . import correction_bot
    try:
        correction_bot.review_and_correct("code", f"bug_fixer:patch:{bug_id}", patch_content)
    except Exception:
        pass

    return {"bug_id": bug_id, "applied": True, "target": str(target), "backup": str(backup_path)}


def run_tests(bug_id: int) -> dict:
    if not config.ALLOW_EXEC:
        raise RuntimeError("running tests requires SHAKTHI_ALLOW_EXEC=1 — same dangerous-tier gate as run_command")
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            raise ValueError(f"no such bug: {bug_id}")

    try:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "discover", "tests"],
            cwd=str(bft.codebase_root()), shell=False, timeout=120, capture_output=True, text=True,
        )
        passed = proc.returncode == 0
        output = (proc.stdout + proc.stderr)[-4000:]
    except subprocess.TimeoutExpired as e:
        # Found by audit.py's own missing-error-handling check, run against
        # this file: this call had no try/except, unlike exec_tools.py's
        # equivalent. A hung test run would have raised unhandled here.
        passed = False
        output = f"test run timed out after 120s\n{(e.stdout or '')[-2000:]}"

    with db.get_conn() as conn:
        was_verified = bug["status"] == "verified"
        db.log_bug_event(conn, bug_id, "tests_run", json.dumps({"passed": passed}))
        db.update_bug(conn, bug_id, status="verified" if passed else "regressed")
        if not passed:
            # A "regression" specifically means a bug that was already
            # verified fixed and has now failed again -- the FIRST test run
            # after applying a patch failing isn't a regression, it's the
            # fix not working; regression_count would over-count if it
            # incremented on every failed run instead of just this case.
            if was_verified:
                db.increment_regression(conn, bug_id)
            db.log_bug_event(conn, bug_id, "regressed", output[-1000:])
    return {"bug_id": bug_id, "passed": passed, "output": output}


def check_regression(bug_id: int) -> dict:
    """Re-run tests for a previously-verified bug. If they now fail, the
    bug flips back to 'regressed' (run_tests already does this) — this
    wrapper just documents the intent for the alert sweep to call."""
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
    if not bug or bug["status"] != "verified":
        return {"bug_id": bug_id, "checked": False, "note": "not in verified status"}
    result = run_tests(bug_id)
    return {"bug_id": bug_id, "checked": True, "regressed": not result["passed"]}


# --- Root Cause Report --------------------------------------------------

def root_cause_report(bug_id: int) -> str:
    """The combined Bug Report / Root Cause Analysis / Risk Assessment /
    Patch Proposal / Test Results output the original Phase 0.4 request
    asked for, as one document -- built from the bugs row, its bug_events
    history, and its patch registry entries, not re-summarized by a model
    (the fields are already structured; formatting them doesn't need one
    more local-model call and one more place a hallucination could creep in)."""
    with db.get_conn() as conn:
        bug = db.get_bug(conn, bug_id)
        if not bug:
            raise ValueError(f"no such bug: {bug_id}")
        events = db.bug_events(conn, bug_id)
        patches = db.list_patches(conn, bug_id=bug_id)

    lines = [
        f"BUG REPORT #{bug['id']} — {bug['title']}",
        "=" * 60,
        f"Severity:     {bug['severity']} ({SEVERITY_LABELS.get(bug['severity'], 'unknown')})",
        f"Status:       {bug['status']}",
        f"Source:       {bug['source']}",
        f"Occurrences:  {bug['occurrence_count']}   Regressions: {bug['regression_count']}",
        "",
        "-- Location --",
        f"File:     {bug['file_path'] or '(not determined)'}",
        f"Function: {bug['function_name'] or '(not determined)'}",
        f"Line:     {bug['line_number'] if bug['line_number'] is not None else '(not determined)'}",
        f"Module:   {bug['module_name'] or '(not determined)'}",
        "",
        "-- Root Cause Analysis --",
        bug["root_cause"] or "(not yet analyzed)",
        "",
        "-- Fix Recommendation --",
        bug["fix_recommendation"] or "(none yet)",
        f"Confidence: {bug['confidence']}/100" if bug["confidence"] is not None else "Confidence: (not rated)",
        "",
        "-- Risk Assessment --",
    ]
    if bug["file_path"] and any(s in bug["file_path"] for s in SENSITIVE_FILES):
        lines.append(f"⚠ Touches a security-sensitive module ({bug['file_path']}) — requires extra scrutiny.")
    else:
        lines.append("No elevated risk flags from the sensitive-file list.")
    lines.append(f"Duplicate of: bug #{bug['duplicate_of']}" if bug["duplicate_of"] else "Not a duplicate/recurrence of a tracked bug.")

    lines += ["", "-- Patch Proposal --"]
    if not patches:
        lines.append("No patch proposed yet.")
    for p in patches:
        lines.append(f"  patch #{p['id']} -> {p['target_file']}  applied={bool(p['applied'])}  ({p['created_at']})")
        if p["diff_path"]:
            lines.append(f"    diff: {p['diff_path']}")

    lines += ["", "-- Lifecycle / Test Results --"]
    for e in events:
        lines.append(f"  [{e['created_at']}] {e['event_type']}")

    return "\n".join(lines)
