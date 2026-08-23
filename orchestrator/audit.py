"""
Full-codebase audit — Phase 0.4. Detection is deterministic static
analysis (Python's own `ast` module for structural checks, not regex
guessing where correctness matters) plus reuse of security.py's pattern
scan. Model calls are used only where judgment genuinely helps: deepening
a bounded sample of the highest-severity findings through the Bug Fixer
pipeline, and a CEO-agent executive summary at the end.

Scope: orchestrator/**/*.py only. The dashboard/ (TypeScript/Next.js) is
NOT covered by these checks -- a Python ast-based analyzer has nothing to
say about TypeScript, and this doesn't pretend otherwise. A real TS audit
would need a different toolchain (eslint, tsc --noEmit), not built here.
"""
import ast
import hashlib
import json
import re
from pathlib import Path

from . import bug_fixer, bugfix_tools as bft
from . import config, db
from . import security as security_mod

RISKY_CALL_NAMES = {"urlopen", "run", "open", "Popen", "check_output", "check_call"}
DEDUPE_WINDOW = 6           # consecutive non-blank lines per duplication block
DEDUPE_MIN_LINE_LEN = 8     # ignore trivial short lines (blank-ish, single tokens) when hashing

SEVERITY_WEIGHTS = {"P0": 20, "P1": 10, "P2": 5, "P3": 2, "P4": 1}


def _python_files() -> list:
    root = bft.codebase_root()
    files = []
    for base in (root / "orchestrator", root / "tests"):
        if base.exists():
            files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def _read_all(files: list) -> dict:
    return {f: f.read_text(errors="replace") for f in files}


# --- Security (reuses security.py's real detection) -------------------------

def check_security(sources: dict) -> list:
    findings = []
    for path, text in sources.items():
        rel = str(path.relative_to(bft.codebase_root()))
        for name, pattern in security_mod.SECRET_PATTERNS.items():
            m = pattern.search(text)
            if m:
                line_no = text.count("\n", 0, m.start()) + 1
                findings.append({"category": "security", "severity": "P0", "file_path": rel, "line_number": line_no,
                                  "description": f"Possible hardcoded secret ({name})",
                                  "recommendation": "Move to an environment variable or manual-entry flag, never a literal."})
        for name, pattern in bug_fixer.DANGEROUS_PATCH_PATTERNS.items():
            m = pattern.search(text)
            if m:
                line_no = text.count("\n", 0, m.start()) + 1
                findings.append({"category": "security", "severity": "P1", "file_path": rel, "line_number": line_no,
                                  "description": f"Dangerous pattern: {name}",
                                  "recommendation": "Review whether this can be replaced with an allowlisted, argv-based call."})
    return findings


# --- Duplicate code (sliding-window line hashing) ---------------------------

def check_duplicate_code(sources: dict) -> list:
    seen = {}  # hash -> (file, line_no)
    findings = []
    for path, text in sources.items():
        rel = str(path.relative_to(bft.codebase_root()))
        lines = [l for l in text.splitlines() if len(l.strip()) >= DEDUPE_MIN_LINE_LEN]
        for i in range(len(lines) - DEDUPE_WINDOW + 1):
            block = "\n".join(lines[i:i + DEDUPE_WINDOW])
            h = hashlib.sha1(block.encode()).hexdigest()
            if h in seen:
                other_file, other_line = seen[h]
                if other_file != rel:  # only flag cross-file duplication, not a file quoting itself
                    findings.append({
                        "category": "duplicate_code", "severity": "P3", "file_path": rel, "line_number": i + 1,
                        "description": f"{DEDUPE_WINDOW}-line block duplicated from {other_file}:{other_line}",
                        "recommendation": "Consider extracting a shared helper if this isn't intentional (e.g. paths.py vs bugfix_tools.py duplicate containment logic, which IS intentional -- see that module's docstring).",
                    })
            else:
                seen[h] = (rel, i + 1)
    return findings


# --- Performance: nested-loop heuristic (AST) --------------------------------

def _max_loop_nesting(node, depth=0) -> int:
    best = depth
    for child in ast.iter_child_nodes(node):
        child_depth = depth + 1 if isinstance(child, (ast.For, ast.While)) else depth
        best = max(best, _max_loop_nesting(child, child_depth))
    return best


def check_performance(sources: dict) -> list:
    findings = []
    for path, text in sources.items():
        rel = str(path.relative_to(bft.codebase_root()))
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                nesting = _max_loop_nesting(node)
                if nesting >= 2:
                    findings.append({
                        "category": "performance", "severity": "P3", "file_path": rel, "line_number": node.lineno,
                        "description": f"Function '{node.name}' has {nesting} levels of nested loops (potential O(n^{nesting}+))",
                        "recommendation": "Review whether this scales with real data volume; not necessarily wrong at current scale.",
                    })
    return findings


# --- Missing error handling (AST) --------------------------------------------

def _calls_risky_function(node) -> list:
    hits = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fn = child.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else None)
            if name in RISKY_CALL_NAMES:
                hits.append((name, child.lineno))
    return hits


def _contains_try(node) -> bool:
    return any(isinstance(child, ast.Try) for child in ast.walk(node))


def check_missing_error_handling(sources: dict) -> list:
    findings = []
    for path, text in sources.items():
        rel = str(path.relative_to(bft.codebase_root()))
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            risky = _calls_risky_function(node)
            if risky and not _contains_try(node):
                calls = ", ".join(sorted({name for name, _ in risky}))
                findings.append({
                    "category": "missing_error_handling", "severity": "P2", "file_path": rel, "line_number": node.lineno,
                    "description": f"Function '{node.name}' calls {calls} with no try/except in the same function",
                    "recommendation": "Confirm the caller handles failure, or wrap here if this is meant to degrade cleanly.",
                })
    return findings


# --- Dead code (module-level defs never referenced elsewhere, AST + text) ---

def check_dead_code(sources: dict) -> list:
    corpus = "\n".join(sources.values())
    findings = []
    for path, text in sources.items():
        rel = str(path.relative_to(bft.codebase_root()))
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue
        for node in tree.body:  # module-level only -- not nested/private helpers
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
                if node.name in ("main",):
                    continue
                occurrences = len(re.findall(rf"\b{re.escape(node.name)}\b", corpus))
                if occurrences <= 1:  # only its own def line
                    findings.append({
                        "category": "dead_code", "severity": "P4", "file_path": rel, "line_number": node.lineno,
                        "description": f"'{node.name}' is defined but not referenced anywhere else in orchestrator/ or tests/",
                        "recommendation": "Verify manually -- dynamic dispatch (e.g. a string key into a dict of handlers) won't show up as a text reference here.",
                    })
    return findings


# --- Unused files -------------------------------------------------------------

def check_unused_files(sources: dict) -> list:
    corpus_by_file = sources
    all_text = "\n".join(sources.values())
    findings = []
    for path in sources:
        if path.name in ("__init__.py",):
            continue
        rel = str(path.relative_to(bft.codebase_root()))
        module_name = path.stem
        others = "\n".join(t for p, t in corpus_by_file.items() if p != path)
        pattern = rf"\b{re.escape(module_name)}\b"
        if not re.search(pattern, others):
            findings.append({
                "category": "unused_file", "severity": "P4", "file_path": rel, "line_number": None,
                "description": f"No other file in orchestrator/ or tests/ appears to import or reference '{module_name}'",
                "recommendation": "Confirm it's not an entrypoint invoked directly (python -m orchestrator.X) before removing.",
            })
    return findings


# --- Missing tests -------------------------------------------------------------

def check_missing_tests(sources: dict) -> list:
    test_files = {p: t for p, t in sources.items() if p.name.startswith("test_")}
    test_corpus = "\n".join(test_files.values())
    findings = []
    for path in sources:
        if path in test_files or path.name == "__init__.py":
            continue
        if "orchestrator" not in path.parts:
            continue
        rel = str(path.relative_to(bft.codebase_root()))
        module_name = path.stem
        if not re.search(rf"\b{re.escape(module_name)}\b", test_corpus):
            findings.append({
                "category": "missing_tests", "severity": "P3", "file_path": rel, "line_number": None,
                "description": f"No test file references '{module_name}' by name",
                "recommendation": "May be covered indirectly through another module's tests -- verify before treating as a real gap.",
            })
    return findings


# --- Orchestration -------------------------------------------------------------

CHECKS = [
    check_security,
    check_duplicate_code,
    check_performance,
    check_missing_error_handling,
    check_dead_code,
    check_unused_files,
    check_missing_tests,
]


def run_static_analysis() -> dict:
    files = _python_files()
    sources = _read_all(files)
    findings = []
    for check in CHECKS:
        findings.extend(check(sources))
    return {"findings": findings, "files_scanned": len(files)}


def run_full_audit(deepen_top_n: int = 3) -> dict:
    """CEO -> Security -> Bug Fixer -> Engineer -> CEO, as specified.

    CEO opens the audit (one line, logged, doesn't gate anything -- there's
    nothing to approve yet, just a stated priority). Security and the
    static checks run in full over every file, deterministic, no model
    calls. Bug Fixer + Engineer only deepen the `deepen_top_n` most severe
    findings into full root-cause-analysis + staged-patch bug records --
    running the full model pipeline on all ~50+ raw findings would mean
    dozens of multi-minute local-model calls for one audit run, which
    isn't a reasonable default. CEO closes with a real executive summary
    over the actual counts, not a generic paragraph.
    """
    with db.get_conn() as conn:
        audit_id = db.insert_audit(conn)

    # Everything below is wrapped: found live, an uncaught exception mid-
    # pipeline (a model timeout during patch generation) left the audits
    # row stuck at status='running' forever, indistinguishable from one
    # still genuinely in progress. Every path out of this function must
    # leave the row in a terminal state.
    try:
        with db.get_conn() as conn:
            task_id = bug_fixer.new_pipeline_task(conn, f"CEO opens audit #{audit_id}")
            order_text = bug_fixer.call_agent(
                conn, task_id, "ceo",
                "The founder has ordered a full codebase audit (bugs, duplicate code, security, "
                "performance, missing error handling, dead code, unused files, missing tests). "
                "In one sentence, state the priority focus for this audit."
            )
            db.update_task(conn, task_id, "done", order_text)

        static = run_static_analysis()
        findings = static["findings"]
        sec_report = security_mod.review(business_id=None)

        finding_ids = []
        with db.get_conn() as conn:
            for f in findings:
                fid = db.insert_audit_finding(conn, audit_id, f["category"], f["severity"], f["file_path"],
                                               f.get("line_number"), f["description"], f.get("recommendation", ""))
                finding_ids.append(fid)
            for sf in sec_report["findings"]:
                db.insert_audit_finding(
                    conn, audit_id, "security", "P1" if sf["type"] == "secret" else "P3",
                    sf.get("file") or sf.get("agent"), None, f"{sf['type']}: {sf['check']}",
                    "From security.review()'s permission/audit-log scan, not the code-pattern scan above.",
                )

        ranked = sorted(zip(findings, finding_ids), key=lambda pair: bug_fixer.SEVERITY_ORDER.get(pair[0]["severity"], 9))
        deepened_bugs, deepening_errors = [], []
        for finding, finding_id in ranked[:deepen_top_n]:
            bug_id = bug_fixer.report_bug(
                f"[audit #{audit_id}] {finding['description']}",
                f"File: {finding['file_path']}:{finding.get('line_number')}\n{finding['description']}\n"
                f"Recommendation: {finding.get('recommendation', '')}",
                severity=finding["severity"],
            )
            with db.get_conn() as conn:
                db.link_finding_to_bug(conn, finding_id, bug_id)
            try:
                analysis = bug_fixer.analyze_bug(bug_id)
                if analysis.get("parsed") and not analysis.get("recurrence_of"):
                    bug_fixer.propose_patch(bug_id)
                deepened_bugs.append(bug_id)
            except Exception as e:
                # One finding's model call failing -- e.g. Engineer timing
                # out generating a full-file patch for a larger file --
                # must not take the whole audit down with it. This is
                # exactly the failure that motivated this try/except: it
                # took down an entire real run before this fix.
                deepening_errors.append({"bug_id": bug_id, "error": str(e)})
                with db.get_conn() as conn:
                    db.log_bug_event(conn, bug_id, "detected", f"deepening stopped early: {e}")

        by_category = {}
        for f in findings:
            by_category[f["category"]] = by_category.get(f["category"], 0) + 1

        with db.get_conn() as conn:
            task_id = bug_fixer.new_pipeline_task(conn, f"CEO executive report for audit #{audit_id}")
            summary_prompt = (
                f"Audit #{audit_id}: {len(findings)} findings across {static['files_scanned']} files.\n"
                f"By category: {json.dumps(by_category)}\n"
                f"{len(deepened_bugs)} findings were escalated for deep root-cause analysis and patch "
                f"proposals: bug ids {deepened_bugs}. {len(deepening_errors)} deepening attempt(s) failed "
                f"(usually a slow-model timeout, not a real problem with the finding).\n\n"
                "IMPORTANT: this is NOT a decision to score. Ignore your usual json decision-block "
                "format completely for this one request. Write 3-4 sentences of plain English prose, "
                "no json, no code fences, no markdown -- a founder reading this on a phone. Cover: "
                "overall health picture, and what to prioritize first. Be direct, not reassuring for "
                "its own sake."
            )
            try:
                exec_summary = bug_fixer.call_agent(conn, task_id, "ceo", summary_prompt)
                db.update_task(conn, task_id, "done", exec_summary)
            except Exception as e:
                exec_summary = (f"(CEO executive summary unavailable: {e}) {len(findings)} findings across "
                                 f"{static['files_scanned']} files; {len(deepened_bugs)} deepened, "
                                 f"{len(deepening_errors)} deepening failures. See audit_findings for detail.")
                db.update_task(conn, task_id, "failed", str(e))

        severity_score = max(0, 100 - sum(SEVERITY_WEIGHTS.get(f["severity"], 1) for f in findings))
        files_affected = len({f["file_path"] for f in findings if f["file_path"]})

        with db.get_conn() as conn:
            db.complete_audit(conn, audit_id, severity_score, len(findings), files_affected, exec_summary)

        # Correction Bot runs automatically after every completed audit --
        # reviews the executive summary's writing quality, review-only.
        from . import correction_bot
        try:
            correction_bot.review_and_correct("writing", f"audit:{audit_id}:executive_summary", exec_summary)
        except Exception:
            pass

        return {
            "audit_id": audit_id, "findings_count": len(findings), "severity_score": severity_score,
            "files_affected": files_affected, "by_category": by_category,
            "deepened_bugs": deepened_bugs, "deepening_errors": deepening_errors,
            "executive_summary": exec_summary,
        }
    except Exception as e:
        with db.get_conn() as conn:
            db.fail_audit(conn, audit_id, str(e))
        raise
