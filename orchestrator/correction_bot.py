"""
SHAKTHI CORRECTION BOT -- Senior Reviewer / Final Quality Controller.

Runs a fixed pipeline on the output of an already-completed task:

  Task Complete -> Correction Review -> QA Review -> Security Review -> Final Approval

Correction Review = deterministic pattern checks (placeholder text, dangerous
code patterns, hardcoded secrets, missing SEO/accessibility basics for HTML
content) PLUS one model call (the correction_bot agent) that reviews the
content and proposes a corrected version -- same "deterministic detection,
model only for judgment/prose" split as security.py and audit.py.

QA Review reuses the existing `qa` agent (PASS/FAIL). Security Review reuses
security.py's SECRET_PATTERNS and bug_fixer's DANGEROUS_PATCH_PATTERNS
directly rather than re-implementing detection. Final Approval reuses
ceo.decide() natively -- "should this correction be applied" is an actual
CEO decision, so no prose-override prompt is needed here (unlike the
executive-summary cases elsewhere in this codebase).

Integrates with CEO (final approval), QA (qa review stage), Security
(deterministic scan reuse), Engineer/Bug Fixer (hooked onto apply_patch()'s
output) and Website Builder (hooked onto run_full_pipeline()'s output) --
see the tail of bug_fixer.py and website_builder.py for the hook calls.
Those hooks are wrapped in try/except and never affect the underlying
pipeline's own return value or tested behavior; a correction-bot failure
must never regress an already-working pipeline.
"""
import json
import re
from datetime import datetime

from . import bug_fixer, ceo, config, db, security

TASK_TYPES = ("code", "writing", "business_report", "website_content", "seo_content")

PLACEHOLDER_PATTERNS = re.compile(
    r"(?i)\b(lorem ipsum|TODO|FIXME|XXX|placeholder text|\[insert[^\]]*\]|coming soon|lorem\b)"
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class CorrectionError(RuntimeError):
    pass


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


def scan_placeholders(content: str) -> list:
    findings = []
    for m in PLACEHOLDER_PATTERNS.finditer(content):
        findings.append({"category": "placeholder_text", "description": f"Placeholder marker found: {m.group(0)!r}"})
    return findings


def scan_code_quality(content: str) -> list:
    """Reuses bug_fixer's dangerous-pattern set and security.py's secret
    patterns directly -- one detector for 'is this code dangerous', not a
    second copy that could drift from the one bug_fixer already uses to
    gate patch application."""
    findings = []
    for name, pattern in bug_fixer.DANGEROUS_PATCH_PATTERNS.items():
        if pattern.search(content):
            findings.append({"category": "code_quality", "description": f"Dangerous pattern: {name}"})
    for name, pattern in security.SECRET_PATTERNS.items():
        if pattern.search(content):
            findings.append({"category": "secret", "description": f"Possible hardcoded secret ({name})"})
    return findings


def scan_website_content(content: str) -> list:
    """For HTML content, reuse WEB-001's SEO/accessibility checks rather
    than re-parsing tags a second way."""
    if "<html" not in content.lower() and "<body" not in content.lower():
        return []
    from . import website_audit as wa
    page = wa._PageParser()
    try:
        page.feed(content)
    except Exception:
        return []
    findings = []
    seo = wa.check_seo_metadata(page)
    if not seo["title"]:
        findings.append({"category": "seo", "description": "Missing <title> tag."})
    if not seo["meta_description"]:
        findings.append({"category": "seo", "description": "Missing meta description."})
    if not seo["single_h1"]:
        findings.append({"category": "seo", "description": f"Found {seo['h1_count']} <h1> tags (expected exactly 1)."})
    a11y = wa.check_accessibility(page)
    if a11y["images_missing_alt"]:
        findings.append({"category": "accessibility", "description": f"{a11y['images_missing_alt']} image(s) missing alt text."})
    if not a11y["html_lang_present"]:
        findings.append({"category": "accessibility", "description": "<html> tag has no lang attribute."})
    return findings


def deterministic_review(task_type: str, content: str) -> list:
    findings = scan_placeholders(content)
    if task_type == "code":
        findings += scan_code_quality(content)
    if task_type in ("website_content", "seo_content"):
        findings += scan_website_content(content)
    return findings


def model_review(conn, task_id: int, task_type: str, content: str, deterministic_findings: list) -> dict:
    prompt = (
        f"Content type: {task_type}\n"
        f"Deterministic checks already found {len(deterministic_findings)} issue(s): "
        f"{json.dumps([f['description'] for f in deterministic_findings])}\n\n"
        f"--- CONTENT TO REVIEW ---\n{content}\n--- END CONTENT ---"
    )
    text = bug_fixer.call_agent(conn, task_id, "correction_bot", prompt)
    parsed = _parse_json_block(text)
    if parsed is None:
        return {"issues": [], "corrected_content": content, "quality_score": None, "raw": text, "parsed": False}
    parsed["parsed"] = True
    parsed.setdefault("corrected_content", content)
    return parsed


def qa_review_correction(conn, task_id: int, original: str, corrected: str) -> dict:
    """Reuses the existing `qa` agent -- same PASS/FAIL convention as every
    other pipeline in this codebase."""
    prompt = (
        "A correction was proposed for a piece of content. Check that the "
        "corrected version is safe to apply (no meaning silently dropped, "
        "no unmet requirements introduced, no unsafe content).\n\n"
        f"--- ORIGINAL ---\n{original}\n--- END ORIGINAL ---\n\n"
        f"--- CORRECTED ---\n{corrected}\n--- END CORRECTED ---"
    )
    text = bug_fixer.call_agent(conn, task_id, "qa", prompt)
    passed = text.strip().upper().startswith("PASS")
    return {"passed": passed, "raw": text}


def security_review_correction(corrected: str) -> dict:
    """Deterministic re-scan of the CORRECTED content -- a correction that
    introduces a new secret or a dangerous pattern must be caught before
    approval, not just the original."""
    findings = []
    for name, pattern in security.SECRET_PATTERNS.items():
        if pattern.search(corrected):
            findings.append({"category": "secret", "description": f"Possible hardcoded secret ({name})"})
    for name, pattern in bug_fixer.DANGEROUS_PATCH_PATTERNS.items():
        if pattern.search(corrected):
            findings.append({"category": "dangerous_pattern", "description": f"Dangerous pattern: {name}"})
    return {"passed": len(findings) == 0, "findings": findings}


def _score(issues_count: int) -> int:
    return max(0, min(100, 100 - issues_count * 10))


def format_report(task_type: str, task_ref: str, correction_score: int, quality_score: int,
                   issues_found: int, issues_fixed: int, final_status: str, timestamp: str) -> str:
    return f"""🩺 SHAKTHI CORRECTION REPORT

Task: {task_ref or task_type}
Type: {task_type}

Correction Score: {correction_score}/100
Quality Score: {quality_score}/100

Issues Found: {issues_found}
Issues Fixed: {issues_fixed}

Final Status:
{final_status}

Timestamp:
{timestamp}"""


def review_and_correct(task_type: str, task_ref: str, content: str, business_id: int = None,
                        telegram_token: str = None, telegram_chat_id: str = None,
                        sheets_credentials: str = None, sheets_id: str = None) -> dict:
    if task_type not in TASK_TYPES:
        raise CorrectionError(f"unknown task_type '{task_type}' -- expected one of {TASK_TYPES}")

    with db.get_conn() as conn:
        correction_id = db.insert_correction(conn, task_type, task_ref, business_id, content)

    try:
        # Sequential, non-nested connection scopes throughout -- ceo.decide()
        # below opens its own connection internally, and a second sqlite3
        # connection can't acquire the write lock while a first one's
        # transaction is still open (found live: "database is locked").
        with db.get_conn() as conn:
            task_id = bug_fixer.new_pipeline_task(conn, f"Correction review: {task_ref or task_type}")

            # --- Correction Review: deterministic + model ---
            det_findings = deterministic_review(task_type, content)
            model_result = model_review(conn, task_id, task_type, content, det_findings)
            corrected_content = model_result.get("corrected_content") or content
            model_issues = model_result.get("issues") or []

            # --- QA Review ---
            qa_result = qa_review_correction(conn, task_id, content, corrected_content)

        all_findings = det_findings + [
            {"category": i.get("category", "inconsistency"), "description": i.get("description", "")}
            for i in model_issues if isinstance(i, dict)
        ]

        # --- Security Review --- (deterministic, no DB access)
        sec_result = security_review_correction(corrected_content)
        all_findings += [{"category": "secret" if f["category"] == "secret" else "dangerous_pattern",
                           "description": f["description"]} for f in sec_result["findings"]]

        issues_found = len(all_findings)
        content_changed = corrected_content.strip() != content.strip()
        issues_fixed = issues_found if (content_changed and qa_result["passed"] and sec_result["passed"]) else 0

        correction_score = _score(len(det_findings) + len(sec_result["findings"]))
        quality_score = model_result.get("quality_score")
        if quality_score is None:
            quality_score = _score(issues_found - issues_fixed)

        # --- Final Approval (CEO) --- ceo.decide() manages its own connection.
        if not qa_result["passed"] or not sec_result["passed"]:
            final_status = "revise"
            decision_reason = "QA or Security review failed the proposed correction."
        else:
            goal = (
                f"Approve applying a correction to {task_type} content ('{task_ref or 'untitled'}')? "
                f"{issues_found} issue(s) found, QA={'pass' if qa_result['passed'] else 'fail'}, "
                f"Security={'pass' if sec_result['passed'] else 'fail'}, content_changed={content_changed}."
            )
            try:
                decision = ceo.decide(goal, business_id=business_id)
                final_status = "approved" if decision.get("status") == "approved" else "revise"
                decision_reason = decision.get("reason", "")
            except Exception as e:
                final_status = "revise"
                decision_reason = f"CEO decision unavailable: {e}"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        summary = (
            f"{issues_found} issue(s) found across correction/QA/security review; "
            f"{issues_fixed} auto-fixed. {decision_reason}"
        )

        with db.get_conn() as conn:
            db.update_task(conn, task_id, "done", summary)
            db.complete_correction(
                conn, correction_id, correction_score, quality_score, issues_found, issues_fixed,
                "pass" if qa_result["passed"] else "fail", "pass" if sec_result["passed"] else "fail",
                final_status, corrected_content, summary,
            )
            for f in all_findings:
                db.insert_correction_finding(conn, correction_id, f["category"], f["description"],
                                              auto_fixed=bool(issues_fixed))

        report_text = format_report(task_type, task_ref, correction_score, quality_score,
                                     issues_found, issues_fixed, final_status, timestamp)

        result = {
            "correction_id": correction_id, "task_type": task_type, "task_ref": task_ref,
            "correction_score": correction_score, "quality_score": quality_score,
            "issues_found": issues_found, "issues_fixed": issues_fixed, "final_status": final_status,
            "corrected_content": corrected_content, "report_text": report_text, "timestamp": timestamp,
            "telegram_sent": False, "sheets_synced": False,
        }

        from . import telegram as tg
        from . import telegram_service as ts
        try:
            token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
            tg.send_message(token, chat_id, report_text, parse_mode=None)
            result["telegram_sent"] = True
        except tg.TelegramError as e:
            result["telegram_error"] = str(e)

        if sheets_credentials and sheets_id:
            from . import sheets
            try:
                state = sheets._load_state()
                client = sheets.get_client(sheets_credentials)
                sheets.sync_correction_history(client, sheets_id, state)
                sheets._save_state(state)
                result["sheets_synced"] = True
            except sheets.SheetsError as e:
                result["sheets_error"] = str(e)
        else:
            result["sheets_error"] = "no Google Sheets credentials provided for this run — DB storage still happened, Sheets did not"

        return result
    except Exception as e:
        with db.get_conn() as conn:
            db.fail_correction(conn, correction_id, str(e))
        raise
