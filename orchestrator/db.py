import re
import sqlite3
from contextlib import contextmanager

from . import config


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(config.SCHEMA_PATH.read_text())


def upsert_agent(conn, agent: dict):
    conn.execute(
        """
        INSERT INTO agents (id, layer, name, default_model_tier, local_model, allowed_scope, allowed_tools, role_prompt)
        VALUES (:id, :layer, :name, :default_model_tier, :local_model, :allowed_scope, :allowed_tools, :role_prompt)
        ON CONFLICT(id) DO UPDATE SET
            layer=excluded.layer, name=excluded.name,
            default_model_tier=excluded.default_model_tier,
            local_model=excluded.local_model,
            allowed_scope=excluded.allowed_scope,
            allowed_tools=excluded.allowed_tools,
            role_prompt=excluded.role_prompt
        """,
        agent,
    )


def get_agent(conn, agent_id: str):
    row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def insert_business(conn, name: str, tenant_id: str = "founder") -> int:
    cur = conn.execute(
        "INSERT INTO businesses (tenant_id, name) VALUES (?, ?)", (tenant_id, name)
    )
    return cur.lastrowid


def insert_site(conn, business_id: int, domain: str, template_id: str, status: str = "planned") -> int:
    cur = conn.execute(
        "INSERT INTO sites (business_id, domain, template_id, status) VALUES (?, ?, ?, ?)",
        (business_id, domain, template_id, status),
    )
    return cur.lastrowid


def insert_task(conn, agent_id: str, goal: str, business_id: int | None, risk_level: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO tasks (agent_id, goal, business_id, risk_level, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (agent_id, goal, business_id, risk_level),
    )
    return cur.lastrowid


def update_task(conn, task_id: int, status: str, result: str):
    conn.execute(
        "UPDATE tasks SET status = ?, result = ? WHERE id = ?",
        (status, result, task_id),
    )


def log_event(conn, task_id: int, event_type: str, payload: str = ""):
    conn.execute(
        "INSERT INTO task_events (task_id, event_type, payload) VALUES (?, ?, ?)",
        (task_id, event_type, payload),
    )


def log_cost(conn, task_id: int, agent_id: str, model: str, provider: str, tokens_in: int, tokens_out: int, cost_usd: float):
    conn.execute(
        """
        INSERT INTO cost_ledger (task_id, agent_id, model, provider, tokens_in, tokens_out, cost_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, agent_id, model, provider, tokens_in, tokens_out, cost_usd),
    )


def insert_memory(conn, layer: str, content: str, business_id: int | None, tags: str = ""):
    conn.execute(
        "INSERT INTO memory_entries (layer, content, business_id, tags) VALUES (?, ?, ?, ?)",
        (layer, content, business_id, tags),
    )


def recent_memory(conn, business_id: int | None, cross_tenant: bool, limit: int = 5):
    # v0.1 retrieval is recency-only. Upgrading this to embedding similarity
    # (nomic-embed-text via Ollama, or pgvector after the Postgres move) is
    # the first thing to change once memory volume grows past what recency
    # alone can usefully rank — see README "Known gaps".
    # id DESC as the real sort key: created_at has only second resolution,
    # so ties from calls in the same second would otherwise sort arbitrarily.
    if cross_tenant:
        rows = conn.execute(
            "SELECT * FROM memory_entries ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM memory_entries WHERE business_id IS ? ORDER BY id DESC LIMIT ?",
            (business_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def cost_summary(conn, since: str | None = None):
    query = """
        SELECT provider, COUNT(*) as calls, SUM(tokens_in) as tokens_in,
               SUM(tokens_out) as tokens_out, SUM(cost_usd) as cost_usd
        FROM cost_ledger
    """
    params = ()
    if since:
        query += " WHERE created_at >= ?"
        params = (since,)
    query += " GROUP BY provider"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Phase 0.2: tool calls ------------------------------------------------

def log_tool_call(conn, task_id: int, agent_id: str, business_id, tool_name: str,
                   params: str, decision: str, denial_reason: str = None,
                   output_summary: str = None, duration_ms: int = None):
    conn.execute(
        """
        INSERT INTO tool_calls (task_id, agent_id, business_id, tool_name, params,
                                 decision, denial_reason, output_summary, duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, agent_id, business_id, tool_name, params, decision,
         denial_reason, output_summary, duration_ms),
    )


def recent_tool_calls(conn, limit: int = 10, decision: str | None = None):
    if decision:
        rows = conn.execute(
            "SELECT * FROM tool_calls WHERE decision = ? ORDER BY id DESC LIMIT ?",
            (decision, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tool_calls ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def update_site(conn, site_id: int, status: str, local_path: str = None):
    conn.execute(
        "UPDATE sites SET status = ?, local_path = ? WHERE id = ?",
        (status, local_path, site_id),
    )


def get_site_for_business(conn, business_id: int):
    row = conn.execute(
        "SELECT * FROM sites WHERE business_id = ? ORDER BY id LIMIT 1", (business_id,)
    ).fetchone()
    return dict(row) if row else None


# --- Phase 0.2: CEO decisions ---------------------------------------------

def insert_decision(conn, task_id, business_id, goal: str, status: str,
                     priority_score: int, risk_score: int, business_impact_score: int,
                     reason: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO decisions (task_id, business_id, goal, status, priority_score,
                                risk_score, business_impact_score, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, business_id, goal, status, priority_score, risk_score,
         business_impact_score, reason),
    )
    return cur.lastrowid


def decisions_since(conn, since_id: int = 0):
    rows = conn.execute("SELECT * FROM decisions WHERE id > ? ORDER BY id", (since_id,)).fetchall()
    return [dict(r) for r in rows]


def cost_ledger_since(conn, since_id: int = 0):
    rows = conn.execute("SELECT * FROM cost_ledger WHERE id > ? ORDER BY id", (since_id,)).fetchall()
    return [dict(r) for r in rows]


def recent_decisions(conn, limit: int = 10):
    rows = conn.execute(
        "SELECT * FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Phase 0.2: finance ----------------------------------------------------

def insert_finance_entry(conn, business_id: int, type_: str, amount: float, description: str = "", category: str = "general") -> int:
    cur = conn.execute(
        "INSERT INTO finance_entries (business_id, type, category, amount, description) VALUES (?, ?, ?, ?, ?)",
        (business_id, type_, category, amount, description),
    )
    return cur.lastrowid


def finance_entries_summary(conn, business_id: int | None = None, since: str | None = None):
    query = "SELECT business_id, type, SUM(amount) as total FROM finance_entries"
    clauses, params = [], []
    if business_id is not None:
        clauses.append("business_id = ?")
        params.append(business_id)
    if since:
        clauses.append("created_at >= ?")
        params.append(since)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " GROUP BY business_id, type"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def finance_entries_by_category(conn, business_id: int | None = None, since: str | None = None, type_: str = "expense"):
    query = "SELECT business_id, category, SUM(amount) as total FROM finance_entries WHERE type = ?"
    params = [type_]
    if business_id is not None:
        query += " AND business_id = ?"
        params.append(business_id)
    if since:
        query += " AND created_at >= ?"
        params.append(since)
    query += " GROUP BY business_id, category"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def list_finance_entries(conn, business_id: int | None = None, since_id: int = 0, type_: str | None = None):
    query = "SELECT * FROM finance_entries WHERE id > ?"
    params = [since_id]
    if business_id is not None:
        query += " AND business_id = ?"
        params.append(business_id)
    if type_:
        query += " AND type = ?"
        params.append(type_)
    query += " ORDER BY id"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def list_businesses(conn):
    rows = conn.execute("SELECT * FROM businesses ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# --- Phase 0.2: security ---------------------------------------------------

def insert_security_report(conn, business_id, score: int, findings_json: str) -> int:
    cur = conn.execute(
        "INSERT INTO security_reports (business_id, score, findings) VALUES (?, ?, ?)",
        (business_id, score, findings_json),
    )
    return cur.lastrowid


def latest_security_report(conn, business_id: int | None = None):
    if business_id is not None:
        row = conn.execute(
            "SELECT * FROM security_reports WHERE business_id = ? ORDER BY id DESC LIMIT 1",
            (business_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM security_reports ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


# --- Phase 0.2: dashboard helpers ------------------------------------------

def active_task_count(conn):
    row = conn.execute("SELECT COUNT(*) as c FROM tasks WHERE status = 'pending'").fetchone()
    return row["c"]


def recent_tasks(conn, limit: int = 10):
    rows = conn.execute(
        "SELECT id, agent_id, business_id, status, risk_level, created_at FROM tasks ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_tasks_full(conn, status: str = None, limit: int = 100):
    if status:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def task_status_counts(conn):
    rows = conn.execute("SELECT status, COUNT(*) as c FROM tasks GROUP BY status").fetchall()
    return {r["status"]: r["c"] for r in rows}


def list_all_memory(conn, layer: str = None, limit: int = 100):
    if layer:
        rows = conn.execute(
            "SELECT * FROM memory_entries WHERE layer = ? ORDER BY id DESC LIMIT ?", (layer, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM memory_entries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def list_agents(conn):
    rows = conn.execute("SELECT * FROM agents ORDER BY layer, id").fetchall()
    return [dict(r) for r in rows]


# --- Phase 0.4: error log ---------------------------------------------------

def log_error(conn, source: str, module: str, message: str, traceback_text: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO error_log (source, module, message, traceback) VALUES (?, ?, ?, ?)",
        (source, module, message, traceback_text),
    )
    return cur.lastrowid


def untriaged_errors(conn, limit: int = 50):
    rows = conn.execute(
        "SELECT * FROM error_log WHERE bug_id IS NULL ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def mark_error_triaged(conn, error_id: int, bug_id: int):
    conn.execute("UPDATE error_log SET bug_id = ? WHERE id = ?", (bug_id, error_id))


# --- Phase 0.4: bugs ---------------------------------------------------------

def insert_bug(conn, title: str, description: str, severity: str, source: str,
                related_task_id=None, related_error_id=None) -> int:
    cur = conn.execute(
        """
        INSERT INTO bugs (title, description, severity, source, related_task_id, related_error_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, description, severity, source, related_task_id, related_error_id),
    )
    return cur.lastrowid


def get_bug(conn, bug_id: int):
    row = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
    return dict(row) if row else None


def update_bug(conn, bug_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE bugs SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), bug_id),
    )


def list_bugs(conn, status: str = None, severity: str = None, limit: int = 50):
    query = "SELECT * FROM bugs"
    clauses, params = [], []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def bugs_since(conn, since_id: int = 0, severity_in=("P0", "P1")):
    placeholders = ",".join("?" * len(severity_in))
    rows = conn.execute(
        f"SELECT * FROM bugs WHERE id > ? AND severity IN ({placeholders}) ORDER BY id",
        (since_id, *severity_in),
    ).fetchall()
    return [dict(r) for r in rows]


def bugs_regressed_since(conn, since_id: int = 0):
    rows = conn.execute(
        "SELECT * FROM bugs WHERE id > ? AND status = 'regressed' ORDER BY id", (since_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def find_bug_by_signature(conn, file_path: str, function_name: str, exclude_bug_id: int):
    """For recurrence detection: an earlier, non-duplicate bug at the same
    (file, function). Excludes the bug being checked itself."""
    if not file_path or not function_name:
        return None
    row = conn.execute(
        """
        SELECT * FROM bugs
        WHERE file_path = ? AND function_name = ? AND id != ? AND duplicate_of IS NULL
        ORDER BY id LIMIT 1
        """,
        (file_path, function_name, exclude_bug_id),
    ).fetchone()
    return dict(row) if row else None


def increment_occurrence(conn, bug_id: int):
    conn.execute("UPDATE bugs SET occurrence_count = occurrence_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (bug_id,))


def increment_regression(conn, bug_id: int):
    conn.execute("UPDATE bugs SET regression_count = regression_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (bug_id,))


def log_bug_event(conn, bug_id: int, event_type: str, payload: str = ""):
    conn.execute(
        "INSERT INTO bug_events (bug_id, event_type, payload) VALUES (?, ?, ?)",
        (bug_id, event_type, payload),
    )


def bug_events(conn, bug_id: int):
    rows = conn.execute("SELECT * FROM bug_events WHERE bug_id = ? ORDER BY id", (bug_id,)).fetchall()
    return [dict(r) for r in rows]


# --- Phase 0.4: patch registry ----------------------------------------------

def insert_patch(conn, bug_id: int, target_file: str, full_file_path: str, diff_path: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO patches (bug_id, target_file, full_file_path, diff_path) VALUES (?, ?, ?, ?)",
        (bug_id, target_file, full_file_path, diff_path),
    )
    return cur.lastrowid


def mark_patch_applied(conn, patch_id: int):
    conn.execute("UPDATE patches SET applied = 1 WHERE id = ?", (patch_id,))


def list_patches(conn, bug_id: int = None, limit: int = 50):
    if bug_id is not None:
        rows = conn.execute("SELECT * FROM patches WHERE bug_id = ? ORDER BY id DESC", (bug_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM patches ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_patch(conn, patch_id: int):
    row = conn.execute("SELECT * FROM patches WHERE id = ?", (patch_id,)).fetchone()
    return dict(row) if row else None


# --- Phase 0.4: audits -------------------------------------------------------

def insert_audit(conn) -> int:
    cur = conn.execute("INSERT INTO audits (status) VALUES ('running')")
    return cur.lastrowid


def complete_audit(conn, audit_id: int, severity_score: int, findings_count: int,
                    files_affected: int, executive_summary: str):
    conn.execute(
        """
        UPDATE audits SET status = 'completed', severity_score = ?, findings_count = ?,
               files_affected = ?, executive_summary = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (severity_score, findings_count, files_affected, executive_summary, audit_id),
    )


def fail_audit(conn, audit_id: int, error_message: str, findings_count: int = 0, files_affected: int = 0):
    """Found live: a mid-pipeline exception (e.g. a model timeout during
    patch generation) previously left the audits row stuck at 'running'
    forever, with no way to tell a genuinely long-running audit apart from
    one that silently died. Always call this from an except clause around
    run_full_audit(), never leave 'running' as a terminal state."""
    conn.execute(
        """
        UPDATE audits SET status = 'failed', findings_count = ?, files_affected = ?,
               executive_summary = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (findings_count, files_affected, f"FAILED: {error_message}", audit_id),
    )


def insert_audit_finding(conn, audit_id: int, category: str, severity: str, file_path: str,
                          line_number, description: str, recommendation: str = "", bug_id=None) -> int:
    cur = conn.execute(
        """
        INSERT INTO audit_findings (audit_id, category, severity, file_path, line_number,
                                     description, recommendation, bug_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (audit_id, category, severity, file_path, line_number, description, recommendation, bug_id),
    )
    return cur.lastrowid


def get_audit(conn, audit_id: int):
    row = conn.execute("SELECT * FROM audits WHERE id = ?", (audit_id,)).fetchone()
    return dict(row) if row else None


def audit_findings(conn, audit_id: int, category: str = None):
    if category:
        rows = conn.execute(
            "SELECT * FROM audit_findings WHERE audit_id = ? AND category = ? ORDER BY id", (audit_id, category)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM audit_findings WHERE audit_id = ? ORDER BY id", (audit_id,)).fetchall()
    return [dict(r) for r in rows]


def list_audits(conn, limit: int = 20):
    rows = conn.execute("SELECT * FROM audits ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def link_finding_to_bug(conn, finding_id: int, bug_id: int):
    conn.execute("UPDATE audit_findings SET bug_id = ? WHERE id = ?", (bug_id, finding_id))


def insert_correction(conn, task_type: str, task_ref: str, business_id: int | None, original_content: str) -> int:
    cur = conn.execute(
        "INSERT INTO corrections (task_type, task_ref, business_id, original_content) VALUES (?, ?, ?, ?)",
        (task_type, task_ref, business_id, original_content),
    )
    return cur.lastrowid


def complete_correction(conn, correction_id: int, correction_score: int, quality_score: int, issues_found: int,
                         issues_fixed: int, qa_status: str, security_status: str, final_status: str,
                         corrected_content: str, summary: str):
    conn.execute(
        """
        UPDATE corrections SET status = 'completed', correction_score = ?, quality_score = ?,
               issues_found = ?, issues_fixed = ?, qa_status = ?, security_status = ?, final_status = ?,
               corrected_content = ?, summary = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (correction_score, quality_score, issues_found, issues_fixed, qa_status, security_status,
         final_status, corrected_content, summary, correction_id),
    )


def fail_correction(conn, correction_id: int, error_message: str):
    conn.execute(
        "UPDATE corrections SET status = 'failed', summary = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (f"FAILED: {error_message}", correction_id),
    )


def insert_correction_finding(conn, correction_id: int, category: str, description: str, auto_fixed: bool) -> int:
    cur = conn.execute(
        "INSERT INTO correction_findings (correction_id, category, description, auto_fixed) VALUES (?, ?, ?, ?)",
        (correction_id, category, description, 1 if auto_fixed else 0),
    )
    return cur.lastrowid


def get_correction(conn, correction_id: int):
    row = conn.execute("SELECT * FROM corrections WHERE id = ?", (correction_id,)).fetchone()
    return dict(row) if row else None


def correction_findings(conn, correction_id: int):
    rows = conn.execute("SELECT * FROM correction_findings WHERE correction_id = ? ORDER BY id", (correction_id,)).fetchall()
    return [dict(r) for r in rows]


def list_corrections(conn, limit: int = 20):
    rows = conn.execute("SELECT * FROM corrections ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --- v4: Sentinel (system_health) -------------------------------------------

def insert_health_snapshot(conn, **fields) -> int:
    cols = ", ".join(fields)
    placeholders = ", ".join("?" * len(fields))
    cur = conn.execute(f"INSERT INTO system_health ({cols}) VALUES ({placeholders})", tuple(fields.values()))
    return cur.lastrowid


def latest_health_snapshot(conn):
    row = conn.execute("SELECT * FROM system_health ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def recent_health_snapshots(conn, limit: int = 50):
    rows = conn.execute("SELECT * FROM system_health ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --- v4: Knowledge -----------------------------------------------------------

def insert_knowledge_doc(conn, category: str, title: str, content: str, tags: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO knowledge_documents (category, title, content, tags) VALUES (?, ?, ?, ?)",
        (category, title, content, tags),
    )
    return cur.lastrowid


def update_knowledge_doc(conn, doc_id: int, title: str = None, content: str = None, tags: str = None):
    fields = {k: v for k, v in {"title": title, "content": content, "tags": tags}.items() if v is not None}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE knowledge_documents SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                 (*fields.values(), doc_id))


def search_knowledge(conn, query: str, category: str = None, limit: int = 20):
    # Matching the whole question as one substring (the previous version of
    # this function) almost never hits -- "where is the wifi password"
    # is not a substring of a document that merely mentions "wifi
    # password". Found live on the first real query. Match on individual
    # significant words (len > 2) instead, any-word-matches, not
    # ranked -- good enough at this document volume; embeddings are the
    # real upgrade path if that stops being true (same note as
    # memory_entries since Phase 0.1).
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2] or [query]
    word_clauses, params = [], []
    for w in words:
        like = f"%{w}%"
        word_clauses.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
        params.extend([like, like, like])
    where = "(" + " OR ".join(word_clauses) + ")"
    if category:
        where += " AND category = ?"
        params.append(category)
    params.append(limit)
    rows = conn.execute(f"SELECT * FROM knowledge_documents WHERE {where} ORDER BY id DESC LIMIT ?", params).fetchall()
    return [dict(r) for r in rows]


def list_knowledge(conn, category: str = None, limit: int = 50):
    if category:
        rows = conn.execute("SELECT * FROM knowledge_documents WHERE category = ? ORDER BY id DESC LIMIT ?", (category, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM knowledge_documents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_knowledge_doc(conn, doc_id: int):
    row = conn.execute("SELECT * FROM knowledge_documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


# --- v4: Buddy ----------------------------------------------------------------

def log_buddy_message(conn, session_id: str, mode: str, message: str, response: str = None, blocked_reason: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO buddy_log (session_id, mode, message, response, blocked_reason) VALUES (?, ?, ?, ?, ?)",
        (session_id, mode, message, response, blocked_reason),
    )
    return cur.lastrowid


def buddy_history(conn, session_id: str, limit: int = 10):
    rows = conn.execute(
        "SELECT * FROM buddy_log WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit)
    ).fetchall()
    return [dict(r) for r in rows][::-1]


# --- v4: Voice ------------------------------------------------------------------

def log_voice_command(conn, identity: str, raw_transcript: str, detected_language: str = None,
                       language_confidence: float = None, routed_agent: str = None, routed_action: str = None,
                       denied_reason: str = None, result_summary: str = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO voice_commands (identity, raw_transcript, detected_language, language_confidence,
                                     routed_agent, routed_action, denied_reason, result_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (identity, raw_transcript, detected_language, language_confidence, routed_agent, routed_action,
         denied_reason, result_summary),
    )
    return cur.lastrowid


def recent_voice_commands(conn, limit: int = 20):
    rows = conn.execute("SELECT * FROM voice_commands ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --- v4: website builder pipeline -------------------------------------------

def insert_website_project(conn, business_id, site_type: str, founder_request: str) -> int:
    cur = conn.execute(
        "INSERT INTO website_projects (business_id, site_type, founder_request) VALUES (?, ?, ?)",
        (business_id, site_type, founder_request),
    )
    return cur.lastrowid


def update_website_project(conn, project_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE website_projects SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), project_id),
    )


def get_website_project(conn, project_id: int):
    row = conn.execute("SELECT * FROM website_projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def list_website_projects(conn, status: str = None, limit: int = 50):
    if status:
        rows = conn.execute(
            "SELECT * FROM website_projects WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM website_projects ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
