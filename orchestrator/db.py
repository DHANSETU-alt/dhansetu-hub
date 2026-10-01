import json
import re
import sqlite3
from contextlib import contextmanager

from . import config


def _connect():
    # Keep concurrent API, worker, and health-check writes from failing on
    # transient SQLite contention. The busy_timeout below is retained as an
    # explicit connection setting because it also applies to connections
    # created by callers that inspect this helper directly.
    conn = sqlite3.connect(config.DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # 30s, not sqlite3's 5s default -- the Worker Pool can run multiple
    # threads against this same file now (each opens its own connection,
    # never shares one across threads -- see worker_pool.py), and at
    # least one existing call path (correction_bot.review_and_correct)
    # holds a connection open across a real model call. A short timeout
    # would surface as spurious "database is locked" errors under real
    # concurrent load; this only ever makes a genuinely-contended write
    # wait longer, never changes query semantics -- safe for every
    # existing single-threaded caller too.
    conn.execute("PRAGMA busy_timeout = 30000")
    # Real incident, 2026-09-16: default rollback-journal mode takes a
    # full-database exclusive lock on every write. With ~25 dashboard pages
    # polling every 1-5s plus the API's own writes, that serialized into
    # "database is locked" errors and request times climbing past 60s
    # (logs/dashboard.log). WAL lets readers proceed during a writer's
    # transaction -- only writer-vs-writer still serializes. `journal_mode`
    # is sticky in the file header, so this is a fast no-op after the first
    # connection; keeping it here (not just a one-off migration) means the
    # setting can't silently regress if the db file is ever recreated.
    conn.execute("PRAGMA journal_mode = WAL")
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
        _migrate_agents_squad_column(conn)
        _migrate_content_queue_platform_column(conn)
        _migrate_system_health_top_process_columns(conn)
        _migrate_initiatives_context_columns(conn)
        _migrate_task_verification_columns(conn)
        _migrate_failure_analyses_agent_column(conn)
        _migrate_payment_transaction_columns(conn)
        # Phase 2 Authentication: users and sessions tables are created via schema.sql
        # (CREATE TABLE IF NOT EXISTS), so no migration function needed


def _migrate_payment_transaction_columns(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(payment_transactions)").fetchall()]
    if "payment_id" not in cols:
        conn.execute("ALTER TABLE payment_transactions ADD COLUMN payment_id TEXT")
    if "customer_email" not in cols:
        conn.execute("ALTER TABLE payment_transactions ADD COLUMN customer_email TEXT")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS payment_transactions_gateway_ref_uq ON payment_transactions(gateway, gateway_ref) WHERE gateway_ref IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS product_subscriptions_gateway_ref_uq ON product_subscriptions(gateway, gateway_ref) WHERE gateway_ref IS NOT NULL")


def _migrate_failure_analyses_agent_column(conn):
    """v3.4 error-proofing plan -- the live failure_analyses table predates
    agent_id, needs the same idempotent ALTER TABLE pattern as the other
    _migrate_* functions above. A fresh DB already has the column from
    schema.sql's CREATE TABLE, so this is a no-op there."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(failure_analyses)").fetchall()]
    if "agent_id" not in cols:
        conn.execute("ALTER TABLE failure_analyses ADD COLUMN agent_id TEXT REFERENCES agents(id)")


def _migrate_task_verification_columns(conn):
    """Completion is not proof: keep independent verification state separate."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if "verification_status" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'unverified'")
    if "verified_by" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN verified_by TEXT")
    if "verified_at" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN verified_at TEXT")


def _migrate_agents_squad_column(conn):
    """CREATE TABLE IF NOT EXISTS never adds a column to a table that
    already exists -- the live agents table predates `squad`, so it needs
    a real, idempotent ALTER TABLE. A fresh DB already has the column from
    schema.sql's CREATE TABLE, so this is a no-op there."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(agents)").fetchall()]
    if "squad" not in cols:
        conn.execute("ALTER TABLE agents ADD COLUMN squad TEXT")


def _migrate_content_queue_platform_column(conn):
    """Same reasoning as agents.squad above -- content_queue predates
    `platform`, needs the same idempotent ALTER TABLE on the live DB."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(content_queue)").fetchall()]
    if "platform" not in cols:
        conn.execute("ALTER TABLE content_queue ADD COLUMN platform TEXT")


def _migrate_system_health_top_process_columns(conn):
    """Same reasoning as agents.squad above -- system_health predates the
    single-runaway-process watchdog check (sentinel.py's _top_process())."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(system_health)").fetchall()]
    if "top_process_cpu_percent" not in cols:
        conn.execute("ALTER TABLE system_health ADD COLUMN top_process_cpu_percent REAL")
    if "top_process_name" not in cols:
        conn.execute("ALTER TABLE system_health ADD COLUMN top_process_name TEXT")


def _migrate_initiatives_context_columns(conn):
    """Same reasoning as agents.squad above -- initiatives predates
    `context`/`cloned_from_id` (added for Smart Copy, Shakthi_OS 3.1.1),
    needs the same idempotent ALTER TABLE on the live DB."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(initiatives)").fetchall()]
    if "context" not in cols:
        conn.execute("ALTER TABLE initiatives ADD COLUMN context TEXT")
    if "cloned_from_id" not in cols:
        conn.execute("ALTER TABLE initiatives ADD COLUMN cloned_from_id INTEGER REFERENCES initiatives(id)")


def upsert_agent(conn, agent: dict):
    agent = {**agent, "squad": agent.get("squad")}
    conn.execute(
        """
        INSERT INTO agents (id, layer, name, default_model_tier, local_model, allowed_scope, allowed_tools, role_prompt, squad)
        VALUES (:id, :layer, :name, :default_model_tier, :local_model, :allowed_scope, :allowed_tools, :role_prompt, :squad)
        ON CONFLICT(id) DO UPDATE SET
            layer=excluded.layer, name=excluded.name,
            default_model_tier=excluded.default_model_tier,
            local_model=excluded.local_model,
            allowed_scope=excluded.allowed_scope,
            allowed_tools=excluded.allowed_tools,
            role_prompt=excluded.role_prompt,
            squad=excluded.squad
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
        "UPDATE tasks SET status = ?, result = ?, verification_status = 'unverified', verified_by = NULL, verified_at = NULL WHERE id = ?",
        (status, result, task_id),
    )


def verify_task(conn, task_id: int, auditor_id: str, accepted: bool, evidence: str):
    """Only a separately named auditor may make completion count as verified."""
    if auditor_id in {"", None} or auditor_id in {"qa", "memory"}:
        raise ValueError("task verification requires an independent auditor identity")
    status = "verified" if accepted else "rejected"
    conn.execute(
        "UPDATE tasks SET verification_status = ?, verified_by = ?, verified_at = CURRENT_TIMESTAMP, result = COALESCE(result, '') || ? WHERE id = ?",
        (status, auditor_id, f"\n\n[Auditor evidence] {evidence}", task_id),
    )


def log_event(conn, task_id: int, event_type: str, payload: str = ""):
    conn.execute(
        "INSERT INTO task_events (task_id, event_type, payload) VALUES (?, ?, ?)",
        (task_id, event_type, payload),
    )


def log_cost(conn, task_id: int, agent_id: str, model: str, provider: str, tokens_in: int, tokens_out: int, cost_usd: float | None):
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


def local_call_intervals_seconds(conn, since: str, provider: str = "ollama") -> list[float]:
    """Real inter-call gaps (seconds) between consecutive cost_ledger rows
    for one provider since a given timestamp. Used to estimate local model
    throughput from actual observed timing, not a guessed number -- callers
    turn this into an average themselves so they can decide what counts as
    "not enough data yet" for their own purposes."""
    rows = conn.execute(
        "SELECT created_at FROM cost_ledger WHERE provider = ? AND created_at >= ? ORDER BY created_at",
        (provider, since),
    ).fetchall()
    timestamps = [r["created_at"] for r in rows]
    if len(timestamps) < 2:
        return []
    from datetime import datetime as _dt
    parsed = [_dt.strptime(t, "%Y-%m-%d %H:%M:%S") for t in timestamps]
    return [(b - a).total_seconds() for a, b in zip(parsed, parsed[1:]) if (b - a).total_seconds() > 0]


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


# --- AI Watchdog -------------------------------------------------------

def insert_watchdog_event(conn, category: str, severity: str, detail: str) -> int:
    cur = conn.execute(
        "INSERT INTO watchdog_events (category, severity, detail) VALUES (?, ?, ?)",
        (category, severity, detail),
    )
    return cur.lastrowid


def recent_watchdog_events(conn, since_id: int = 0, limit: int = 200):
    rows = conn.execute(
        "SELECT * FROM watchdog_events WHERE id > ? ORDER BY id DESC LIMIT ?",
        (since_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_file_hash(conn, path: str):
    row = conn.execute("SELECT sha256 FROM watchdog_file_hashes WHERE path = ?", (path,)).fetchone()
    return row["sha256"] if row else None


def set_file_hash(conn, path: str, sha256: str):
    conn.execute(
        "INSERT INTO watchdog_file_hashes (path, sha256, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(path) DO UPDATE SET sha256 = excluded.sha256, updated_at = CURRENT_TIMESTAMP",
        (path, sha256),
    )


# --- Phase 0.2: dashboard helpers ------------------------------------------

def agent_reality_summary(conn) -> dict:
    """Answers a real founder question (2026-09-16): 'is it really agents
    working, or only Claude?' All-time, real counts -- no sampling, no
    estimation. status_counts and provider_counts both come straight from
    tasks/cost_ledger; never_run_agents is a real set difference, not a
    guess. This is what replaced the static architecture-diagram.html
    (which showed the routing.run_task CODE PATH, not whether it's
    actually being exercised)."""
    status_counts = {
        row["status"]: row["n"]
        for row in conn.execute("SELECT status, COUNT(*) as n FROM tasks GROUP BY status").fetchall()
    }
    provider_counts = {
        row["provider"]: row["n"]
        for row in conn.execute("SELECT provider, COUNT(*) as n FROM cost_ledger GROUP BY provider").fetchall()
    }
    total_agents = conn.execute("SELECT COUNT(*) as n FROM agents").fetchone()["n"]
    ever_run_ids = {r["agent_id"] for r in conn.execute("SELECT DISTINCT agent_id FROM tasks").fetchall()}
    all_agents = conn.execute("SELECT id, name FROM agents ORDER BY id").fetchall()
    never_run = [dict(a) for a in all_agents if a["id"] not in ever_run_ids]
    return {
        "status_counts": status_counts,
        "provider_counts": provider_counts,
        "total_agents": total_agents,
        "ever_run_agent_count": len(ever_run_ids),
        "never_run_agents": never_run,
        "anthropic_key_configured": bool(config.ANTHROPIC_API_KEY),
    }


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


def recent_task_events(conn, limit: int = 50):
    """Real event stream for the Founder Command Center logs panel --
    joins task_events with its parent task so each log line carries real
    agent/goal context, not just a bare event_type."""
    rows = conn.execute(
        """SELECT e.id, e.task_id, e.event_type, e.payload, e.created_at,
                  t.agent_id, t.goal, t.status AS task_status, t.risk_level
           FROM task_events e JOIN tasks t ON t.id = e.task_id
           ORDER BY e.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


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


def insert_payment_link(conn, razorpay_link_id: str, short_url: str, amount_inr: float, description: str,
                         customer_name: str = None, customer_contact: str = None, reference_id: str = None,
                         status: str = "created") -> int:
    cur = conn.execute(
        """
        INSERT INTO payment_links (razorpay_link_id, short_url, amount_inr, description,
                                    customer_name, customer_contact, reference_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (razorpay_link_id, short_url, amount_inr, description, customer_name, customer_contact, reference_id, status),
    )
    return cur.lastrowid


def update_payment_link_status(conn, razorpay_link_id: str, status: str):
    conn.execute(
        "UPDATE payment_links SET status = ?, last_checked_at = CURRENT_TIMESTAMP WHERE razorpay_link_id = ?",
        (status, razorpay_link_id),
    )


def get_payment_link(conn, razorpay_link_id: str):
    row = conn.execute("SELECT * FROM payment_links WHERE razorpay_link_id = ?", (razorpay_link_id,)).fetchone()
    return dict(row) if row else None


def list_payment_links(conn, status: str = None, limit: int = 50):
    if status:
        rows = conn.execute(
            "SELECT * FROM payment_links WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM payment_links ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def insert_website_review(conn, url: str, business_id: int | None) -> int:
    cur = conn.execute("INSERT INTO website_reviews (url, business_id) VALUES (?, ?)", (url, business_id))
    return cur.lastrowid


def complete_website_review(conn, review_id: int, seo_score: int, conversion_score: int, ui_score: int,
                             deployment_ready: bool, findings_count: int, summary: str):
    conn.execute(
        """
        UPDATE website_reviews SET status = 'completed', seo_score = ?, conversion_score = ?, ui_score = ?,
               deployment_ready = ?, findings_count = ?, summary = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (seo_score, conversion_score, ui_score, 1 if deployment_ready else 0, findings_count, summary, review_id),
    )


def fail_website_review(conn, review_id: int, error_message: str):
    conn.execute(
        "UPDATE website_reviews SET status = 'failed', summary = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (f"FAILED: {error_message}", review_id),
    )


def insert_website_review_finding(conn, review_id: int, category: str, severity: str, description: str) -> int:
    cur = conn.execute(
        "INSERT INTO website_review_findings (review_id, category, severity, description) VALUES (?, ?, ?, ?)",
        (review_id, category, severity, description),
    )
    return cur.lastrowid


def get_website_review(conn, review_id: int):
    row = conn.execute("SELECT * FROM website_reviews WHERE id = ?", (review_id,)).fetchone()
    return dict(row) if row else None


def website_review_findings(conn, review_id: int):
    rows = conn.execute("SELECT * FROM website_review_findings WHERE review_id = ? ORDER BY id", (review_id,)).fetchall()
    return [dict(r) for r in rows]


def list_website_reviews(conn, limit: int = 20):
    rows = conn.execute("SELECT * FROM website_reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def insert_payment_transaction(conn, gateway: str, gateway_ref: str, amount: float, currency: str, description: str,
                                customer_name: str = None, customer_contact: str = None, customer_email: str = None,
                                business_id: int = None, url_or_link: str = None, status: str = "created") -> int:
    cur = conn.execute(
        """
        INSERT INTO payment_transactions (gateway, gateway_ref, amount, currency, description, customer_name,
                                           customer_contact, customer_email, business_id, url_or_link, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (gateway, gateway_ref, amount, currency, description, customer_name, customer_contact, customer_email,
         business_id, url_or_link, status),
    )
    return cur.lastrowid


def update_payment_transaction_status(conn, gateway_ref: str, status: str):
    conn.execute(
        "UPDATE payment_transactions SET status = ? WHERE gateway_ref = ?",
        (status, gateway_ref),
    )


def set_payment_transaction_paid(conn, gateway_ref: str, payment_id: str):
    conn.execute("UPDATE payment_transactions SET status = 'paid', payment_id = ? WHERE gateway_ref = ?", (payment_id, gateway_ref))


def get_payment_transaction(conn, gateway_ref: str):
    row = conn.execute("SELECT * FROM payment_transactions WHERE gateway_ref = ?", (gateway_ref,)).fetchone()
    return dict(row) if row else None


def get_payment_transaction_by_payment_id(conn, payment_id: str):
    row = conn.execute("SELECT * FROM payment_transactions WHERE payment_id = ?", (payment_id,)).fetchone()
    return dict(row) if row else None


def list_payment_transactions(conn, gateway: str = None, limit: int = 50):
    if gateway:
        rows = conn.execute(
            "SELECT * FROM payment_transactions WHERE gateway = ? ORDER BY id DESC LIMIT ?", (gateway, limit)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM payment_transactions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --- Worker Pool -------------------------------------------------------

def upsert_worker(conn, name: str, worker_type: str, concurrency_limit: int) -> int:
    cur = conn.execute(
        """
        INSERT INTO workers (name, worker_type, concurrency_limit) VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET worker_type = excluded.worker_type, concurrency_limit = excluded.concurrency_limit
        """,
        (name, worker_type, concurrency_limit),
    )
    row = conn.execute("SELECT id FROM workers WHERE name = ?", (name,)).fetchone()
    return row["id"]


def mark_worker_busy(conn, worker_id: int):
    conn.execute("UPDATE workers SET status = 'busy', last_active_at = CURRENT_TIMESTAMP WHERE id = ?", (worker_id,))


def mark_worker_idle(conn, worker_id: int, succeeded: bool):
    if succeeded:
        conn.execute(
            "UPDATE workers SET status = 'idle', tasks_completed = tasks_completed + 1, last_active_at = CURRENT_TIMESTAMP WHERE id = ?",
            (worker_id,),
        )
    else:
        conn.execute(
            "UPDATE workers SET status = 'idle', tasks_failed = tasks_failed + 1, last_active_at = CURRENT_TIMESTAMP WHERE id = ?",
            (worker_id,),
        )


def mark_worker_failed(conn, worker_id: int):
    conn.execute(
        "UPDATE workers SET status = 'failed', tasks_failed = tasks_failed + 1, last_active_at = CURRENT_TIMESTAMP WHERE id = ?",
        (worker_id,),
    )


def list_workers(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM workers ORDER BY worker_type, name").fetchall()]


def enqueue_work(conn, kind: str, payload: str, priority: int = 5) -> int:
    cur = conn.execute("INSERT INTO work_queue (kind, payload, priority) VALUES (?, ?, ?)", (kind, payload, priority))
    return cur.lastrowid


def queue_depth(conn, status: str = "queued") -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM work_queue WHERE status = ?", (status,)).fetchone()
    return row["n"]


def next_queued_work(conn, limit: int):
    rows = conn.execute(
        "SELECT * FROM work_queue WHERE status = 'queued' ORDER BY priority ASC, id ASC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def mark_work_running(conn, work_id: int, worker_type: str, worker_id: int):
    conn.execute(
        "UPDATE work_queue SET status = 'running', assigned_worker_type = ?, assigned_worker_id = ?, started_at = CURRENT_TIMESTAMP WHERE id = ?",
        (worker_type, worker_id, work_id),
    )


def complete_work(conn, work_id: int, result: str):
    conn.execute(
        "UPDATE work_queue SET status = 'done', result = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (result, work_id),
    )


def fail_work(conn, work_id: int, error: str):
    conn.execute(
        "UPDATE work_queue SET status = 'failed', error = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (error, work_id),
    )


def list_work_queue(conn, status: str = None, limit: int = 50):
    if status:
        rows = conn.execute("SELECT * FROM work_queue WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM work_queue ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# --- Emergency Response Team (incidents) --------------------------------

def next_incident_number(conn, year: int) -> str:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM incidents WHERE incident_number LIKE ?", (f"INC-{year}-%",)
    ).fetchone()
    return f"INC-{year}-{row['n'] + 1:03d}"


def insert_incident(conn, incident_number: str, incident_type: str, severity: str, owner: str,
                     support_team: str, description: str, detected_by: str = "manual") -> int:
    cur = conn.execute(
        """
        INSERT INTO incidents (incident_number, incident_type, severity, owner, support_team, description, detected_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (incident_number, incident_type, severity, owner, support_team, description, detected_by),
    )
    return cur.lastrowid


def update_incident_status(conn, incident_id: int, status: str):
    extra_col = {"ACKNOWLEDGED": "acknowledged_at", "RESOLVED": "resolved_at", "CLOSED": "closed_at"}.get(status)
    if extra_col:
        conn.execute(f"UPDATE incidents SET status = ?, {extra_col} = CURRENT_TIMESTAMP WHERE id = ?", (status, incident_id))
    else:
        conn.execute("UPDATE incidents SET status = ? WHERE id = ?", (status, incident_id))


def update_incident_fields(conn, incident_id: int, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE incidents SET {cols} WHERE id = ?", (*fields.values(), incident_id))


def get_incident(conn, incident_id: int = None, incident_number: str = None):
    if incident_number:
        row = conn.execute("SELECT * FROM incidents WHERE incident_number = ?", (incident_number,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return dict(row) if row else None


def list_incidents(conn, status: str = None, severity: str = None, limit: int = 100):
    query, params = "SELECT * FROM incidents", []
    clauses = []
    if status:
        clauses.append("status = ?"); params.append(status)
    if severity:
        clauses.append("severity = ?"); params.append(severity)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"; params.append(limit)
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def insert_incident_event(conn, incident_id: int, event_type: str, detail: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO incident_events (incident_id, event_type, detail) VALUES (?, ?, ?)",
        (incident_id, event_type, detail),
    )
    return cur.lastrowid


def incident_events(conn, incident_id: int):
    rows = conn.execute("SELECT * FROM incident_events WHERE incident_id = ? ORDER BY id", (incident_id,)).fetchall()
    return [dict(r) for r in rows]


# --- Pricing / usage gating ----------------------------------------------

def get_usage(conn, email: str, product: str):
    row = conn.execute("SELECT * FROM product_usage WHERE email = ? AND product = ?", (email, product)).fetchone()
    return dict(row) if row else None


def increment_usage(conn, email: str, product: str) -> int:
    conn.execute(
        """
        INSERT INTO product_usage (email, product, use_count) VALUES (?, ?, 1)
        ON CONFLICT(email, product) DO UPDATE SET use_count = use_count + 1, last_used_at = CURRENT_TIMESTAMP
        """,
        (email, product),
    )
    row = conn.execute("SELECT use_count FROM product_usage WHERE email = ? AND product = ?", (email, product)).fetchone()
    return row["use_count"]


def get_active_subscription(conn, email: str, product: str):
    # valid_until IS NULL means a one-time/lifetime purchase that never
    # expires (see pricing.py's is_one_time products) -- NULL comparisons
    # in SQL are never true, so "valid_until >= datetime('now')" alone
    # would silently treat every lifetime customer as having no active
    # subscription. Purely additive: every pre-existing product always
    # sets a real valid_until date, never NULL, so this changes nothing
    # for them.
    row = conn.execute(
        "SELECT * FROM product_subscriptions WHERE email = ? AND product = ? AND status = 'active' "
        "AND (valid_until IS NULL OR valid_until >= datetime('now')) ORDER BY id DESC LIMIT 1",
        (email, product),
    ).fetchone()
    return dict(row) if row else None


def count_paid_transactions_for_product(conn, product: str) -> int:
    """Real count of completed payments for a product going through the
    Razorpay Orders/Checkout.js flow (payment_transactions table) --
    distinct from count_active_subscriptions below, which covers the
    OLDER Payment-Links flow's separate product_subscriptions table.
    Two different tables because two payment flows were built at
    different times against different schemas; unifying them is a real
    follow-up, not done here. Matches on the exact product id stored in
    `description` at order-creation time (see
    cli.py's _cmd_create_razorpay_order) -- never a prefix/LIKE match,
    which could double-count or miss rows depending on what a receipt
    string happens to contain."""
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM payment_transactions WHERE description = ? AND status = 'paid'",
        (product,),
    ).fetchone()
    return row["c"]


def count_active_subscriptions(conn, product: str) -> int:
    """Real count of customers who've actually completed payment for a
    product -- used to enforce a hard cap (e.g. 'first 300 customers').
    Counts 'active' status only, never 'pending' -- an unpaid/abandoned
    checkout must never occupy a slot."""
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM product_subscriptions WHERE product = ? AND status = 'active'",
        (product,),
    ).fetchone()
    return row["c"]


def insert_subscription(conn, email: str, product: str, amount_inr: float, gateway: str, gateway_ref: str = None,
                         status: str = "pending", valid_until: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO product_subscriptions (email, product, status, valid_until, amount_inr, gateway, gateway_ref) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (email, product, status, valid_until, amount_inr, gateway, gateway_ref),
    )
    return cur.lastrowid


def get_subscription_by_gateway_ref(conn, gateway: str, gateway_ref: str):
    row = conn.execute("SELECT * FROM product_subscriptions WHERE gateway = ? AND gateway_ref = ?", (gateway, gateway_ref)).fetchone()
    return dict(row) if row else None


def cancel_subscription_by_gateway_ref(conn, gateway: str, gateway_ref: str):
    conn.execute("UPDATE product_subscriptions SET status = 'cancelled' WHERE gateway = ? AND gateway_ref = ?", (gateway, gateway_ref))


def activate_subscription(conn, subscription_id: int, valid_until: str):
    conn.execute("UPDATE product_subscriptions SET status = 'active', valid_until = ? WHERE id = ?",
                 (valid_until, subscription_id))


def get_subscription(conn, subscription_id: int):
    """Real gap found 2026-09-10 (Task 15 audit): pricing.confirm_subscription_paid()
    had no way to look up which product a subscription_id belongs to, so it
    unconditionally set a 365-day valid_until on every confirmed payment --
    including blackboxops_os_starter/growth, the founder's actual one-time
    LIFETIME purchases (is_one_time=True). This getter is what lets that
    function check the product before deciding whether to expire it."""
    row = conn.execute("SELECT * FROM product_subscriptions WHERE id = ?", (subscription_id,)).fetchone()
    return dict(row) if row else None


def list_subscriptions(conn, product: str = None, status: str = None, limit: int = 100):
    query, params = "SELECT * FROM product_subscriptions", []
    clauses = []
    if product:
        clauses.append("product = ?"); params.append(product)
    if status:
        clauses.append("status = ?"); params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"; params.append(limit)
    return [dict(r) for r in conn.execute(query, params).fetchall()]


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


# --- Sales / leads ------------------------------------------------------

def insert_lead(conn, business_id, name: str, email: str, contact: str, source: str, notes: str = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO leads (business_id, name, email, contact, source, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (business_id, name, email, contact, source, notes),
    )
    return cur.lastrowid


def get_lead(conn, lead_id: int):
    row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    return dict(row) if row else None


def update_lead(conn, lead_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE leads SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), lead_id),
    )


def list_leads(conn, status: str = None, owner: str = None, limit: int = 50):
    query, params = "SELECT * FROM leads", []
    clauses = []
    if status:
        clauses.append("status = ?"); params.append(status)
    if owner:
        clauses.append("owner = ?"); params.append(owner)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def log_lead_event(conn, lead_id: int, event_type: str, payload: str = "", task_id: int = None):
    conn.execute(
        "INSERT INTO lead_events (lead_id, event_type, payload, task_id) VALUES (?, ?, ?, ?)",
        (lead_id, event_type, payload, task_id),
    )


def list_lead_events(conn, lead_id: int, limit: int = 50):
    rows = conn.execute(
        "SELECT * FROM lead_events WHERE lead_id = ? ORDER BY id DESC LIMIT ?", (lead_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Client Success ------------------------------------------------------

def insert_client_health_score(conn, lead_id: int, business_id, score: int, signals_json: str) -> int:
    cur = conn.execute(
        "INSERT INTO client_health_scores (lead_id, business_id, score, signals) VALUES (?, ?, ?, ?)",
        (lead_id, business_id, score, signals_json),
    )
    return cur.lastrowid


def latest_client_health_score(conn, lead_id: int):
    row = conn.execute(
        "SELECT * FROM client_health_scores WHERE lead_id = ? ORDER BY id DESC LIMIT 1", (lead_id,)
    ).fetchone()
    return dict(row) if row else None


def list_client_health_scores(conn, since_id: int = 0, limit: int = 100):
    rows = conn.execute(
        "SELECT * FROM client_health_scores WHERE id > ? ORDER BY id DESC LIMIT ?", (since_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def log_client_health_event(conn, lead_id: int, event_type: str, payload: str = "", task_id: int = None):
    conn.execute(
        "INSERT INTO client_health_events (lead_id, event_type, payload, task_id) VALUES (?, ?, ?, ?)",
        (lead_id, event_type, payload, task_id),
    )


def list_client_health_events(conn, lead_id: int, limit: int = 50):
    rows = conn.execute(
        "SELECT * FROM client_health_events WHERE lead_id = ? ORDER BY id DESC LIMIT ?", (lead_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Marketing / content queue ------------------------------------------

def insert_content(conn, business_id, content_type: str, variant_label: str, target: str,
                    content: str, icp_fit_score: float = None, platform: str = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO content_queue (business_id, content_type, variant_label, target, content, icp_fit_score, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (business_id, content_type, variant_label, target, content, icp_fit_score, platform),
    )
    return cur.lastrowid


def get_content(conn, content_id: int):
    row = conn.execute("SELECT * FROM content_queue WHERE id = ?", (content_id,)).fetchone()
    return dict(row) if row else None


def update_content_status(conn, content_id: int, status: str):
    conn.execute("UPDATE content_queue SET status = ? WHERE id = ?", (status, content_id))


def list_content_queue(conn, content_type: str = None, status: str = None, limit: int = 50):
    query, params = "SELECT * FROM content_queue", []
    clauses = []
    if content_type:
        clauses.append("content_type = ?"); params.append(content_type)
    if status:
        clauses.append("status = ?"); params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Daily team work register --------------------------------------------

def insert_team_member(conn, business_id, name: str, role: str = None, contact: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO team_members (business_id, name, role, contact) VALUES (?, ?, ?, ?)",
        (business_id, name, role, contact),
    )
    return cur.lastrowid


def get_team_member(conn, worker_id: int):
    row = conn.execute("SELECT * FROM team_members WHERE id = ?", (worker_id,)).fetchone()
    return dict(row) if row else None


def list_team_members(conn, business_id: int = None, status: str = None):
    query, params = "SELECT * FROM team_members", []
    clauses = []
    if business_id is not None:
        clauses.append("business_id = ?"); params.append(business_id)
    if status:
        clauses.append("status = ?"); params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY name"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def upsert_daily_work_log(conn, worker_id: int, business_id, work_date: str, present: bool,
                           hours_worked: float = None, work_assigned: str = None,
                           work_done: str = None, notes: str = None) -> int:
    """One real entry per worker per day -- a second log_day() call for the
    same worker/date corrects that day's entry (same as crossing out and
    rewriting a line in a physical register), it doesn't create a duplicate."""
    cur = conn.execute(
        """
        INSERT INTO daily_work_logs (worker_id, business_id, work_date, present, hours_worked, work_assigned, work_done, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(worker_id, work_date) DO UPDATE SET
            present=excluded.present, hours_worked=excluded.hours_worked,
            work_assigned=excluded.work_assigned, work_done=excluded.work_done,
            notes=excluded.notes, updated_at=CURRENT_TIMESTAMP
        """,
        (worker_id, business_id, work_date, 1 if present else 0, hours_worked, work_assigned, work_done, notes),
    )
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM daily_work_logs WHERE worker_id = ? AND work_date = ?", (worker_id, work_date)
    ).fetchone()
    return row["id"]


def get_daily_work_log(conn, worker_id: int, work_date: str):
    row = conn.execute(
        "SELECT * FROM daily_work_logs WHERE worker_id = ? AND work_date = ?", (worker_id, work_date)
    ).fetchone()
    return dict(row) if row else None


def list_daily_work_logs(conn, worker_id: int = None, business_id: int = None,
                          work_date: str = None, date_from: str = None, date_to: str = None):
    query, params = "SELECT * FROM daily_work_logs", []
    clauses = []
    if worker_id is not None:
        clauses.append("worker_id = ?"); params.append(worker_id)
    if business_id is not None:
        clauses.append("business_id = ?"); params.append(business_id)
    if work_date:
        clauses.append("work_date = ?"); params.append(work_date)
    if date_from:
        clauses.append("work_date >= ?"); params.append(date_from)
    if date_to:
        clauses.append("work_date <= ?"); params.append(date_to)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY work_date DESC, worker_id"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Agent skill test / review -------------------------------------------

def insert_skill_review(conn, agent_id: str, test_goal: str, response: str, relevance_score,
                         guardrails_score, clarity_score, history_score, has_history: bool,
                         total_score: int, deterministic_check: str = None,
                         possible_fabrication: bool = False, notes: str = None, task_id: int = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO skill_reviews (agent_id, test_goal, response, relevance_score, guardrails_score,
            clarity_score, history_score, has_history, total_score, deterministic_check,
            possible_fabrication, notes, task_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (agent_id, test_goal, response, relevance_score, guardrails_score, clarity_score, history_score,
         1 if has_history else 0, total_score, deterministic_check, 1 if possible_fabrication else 0, notes, task_id),
    )
    return cur.lastrowid


def latest_skill_reviews(conn):
    """Most recent review per agent -- a re-run replaces the prior score in
    this view, it doesn't average with it (a re-test should reflect current
    behavior, not be diluted by an old run)."""
    rows = conn.execute(
        """
        SELECT sr.* FROM skill_reviews sr
        INNER JOIN (SELECT agent_id, MAX(id) AS max_id FROM skill_reviews GROUP BY agent_id) latest
          ON sr.agent_id = latest.agent_id AND sr.id = latest.max_id
        ORDER BY sr.total_score ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def list_skill_reviews(conn, agent_id: str = None, limit: int = 50):
    query, params = "SELECT * FROM skill_reviews", []
    if agent_id:
        query += " WHERE agent_id = ?"; params.append(agent_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Dhansetu AI: courses -------------------------------------------------

def insert_course(conn, business_id, title: str, language: str = "gu", source: str = "manual") -> int:
    cur = conn.execute(
        "INSERT INTO courses (business_id, title, language, source) VALUES (?, ?, ?, ?)",
        (business_id, title, language, source),
    )
    return cur.lastrowid


def get_course(conn, course_id: int):
    row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    return dict(row) if row else None


def update_course(conn, course_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE courses SET {set_clause} WHERE id = ?", (*fields.values(), course_id))


def list_courses(conn, business_id: int = None, status: str = None, limit: int = 50):
    query, params = "SELECT * FROM courses", []
    clauses = []
    if business_id is not None:
        clauses.append("business_id = ?"); params.append(business_id)
    if status:
        clauses.append("status = ?"); params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Dhansetu AI: link tree -----------------------------------------------

def insert_link(conn, business_id, title: str, url: str, sort_order: int = 0) -> int:
    cur = conn.execute(
        "INSERT INTO link_tree_entries (business_id, title, url, sort_order) VALUES (?, ?, ?, ?)",
        (business_id, title, url, sort_order),
    )
    return cur.lastrowid


def list_links(conn, business_id: int = None, active_only: bool = True):
    query, params = "SELECT * FROM link_tree_entries", []
    clauses = []
    if business_id is not None:
        clauses.append("business_id = ?"); params.append(business_id)
    if active_only:
        clauses.append("active = 1")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY sort_order, id"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- blackboxOps_OS onboarding: business discovery (Stage 1 only) --------

def insert_business_discovery(conn, fields: dict) -> int:
    cols = ["business_name", "industry", "website", "business_model", "target_customer",
            "revenue_streams", "team_size", "monthly_revenue_range", "main_challenges",
            "preferred_tools", "current_software", "growth_goal_12mo"]
    values = [fields.get(c) for c in cols]
    placeholders = ", ".join("?" for _ in cols)
    cur = conn.execute(
        f"INSERT INTO business_discoveries ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )
    return cur.lastrowid


def get_business_discovery(conn, discovery_id: int):
    row = conn.execute("SELECT * FROM business_discoveries WHERE id = ?", (discovery_id,)).fetchone()
    return dict(row) if row else None


def update_business_discovery(conn, discovery_id: int, **fields):
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE business_discoveries SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), discovery_id),
    )


def list_business_discoveries(conn, status: str = None, limit: int = 50):
    query, params = "SELECT * FROM business_discoveries", []
    if status:
        query += " WHERE status = ?"; params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Initiative tracker (founder-facing "Task 1, Task 2, ...") -----------

def insert_initiative(conn, title: str, artifact_url: str = None, track: str = "task") -> int:
    """track: 'task' (web-based work, Task N) or 'project' (big cross-platform
    software dev -- Mac/Windows/Linux/iOS/Android, Project N). Each track has
    its own independent seq numbering -- see feedback_task_vs_project memory."""
    next_seq = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM initiatives WHERE track = ?", (track,)
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO initiatives (track, seq, title, artifact_url) VALUES (?, ?, ?, ?)",
        (track, next_seq, title, artifact_url),
    )
    return cur.lastrowid


def add_initiative_milestone(conn, initiative_id: int, title: str, done: bool = False) -> int:
    cur = conn.execute(
        "INSERT INTO initiative_milestones (initiative_id, title, done) VALUES (?, ?, ?)",
        (initiative_id, title, int(done)),
    )
    if done:
        conn.execute("UPDATE initiative_milestones SET done_at = CURRENT_TIMESTAMP WHERE id = ?", (cur.lastrowid,))
    return cur.lastrowid


def set_milestone_done(conn, milestone_id: int, done: bool = True):
    if done:
        conn.execute(
            "UPDATE initiative_milestones SET done = 1, done_at = CURRENT_TIMESTAMP WHERE id = ?",
            (milestone_id,),
        )
    else:
        conn.execute(
            "UPDATE initiative_milestones SET done = 0, done_at = NULL WHERE id = ?",
            (milestone_id,),
        )


def set_initiative_status(conn, initiative_id: int, status: str):
    conn.execute(
        "UPDATE initiatives SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, initiative_id),
    )


def clone_initiative(conn, source_id: int, new_title: str = None, note: str = None) -> int:
    """Smart Copy (Shakthi_OS 3.1.1): clone an initiative as a starting
    template for a new one. Milestones come along as a fresh (undone)
    checklist -- the new initiative is real, unstarted work, not a copy of
    someone else's progress. `context` carries a synthesized brief (title,
    track, source milestone titles, founder's note) so the agent picking up
    the new initiative has the full picture without a separate catch-up."""
    src = conn.execute("SELECT * FROM initiatives WHERE id = ?", (source_id,)).fetchone()
    if not src:
        raise ValueError(f"no initiative with id {source_id}")
    src = dict(src)
    track = src["track"]
    title = new_title or f"{src['title']} (copy)"

    source_milestones = [
        r["title"] for r in conn.execute(
            "SELECT title FROM initiative_milestones WHERE initiative_id = ? ORDER BY id ASC",
            (source_id,),
        ).fetchall()
    ]
    context = json.dumps({
        "cloned_from_id": source_id,
        "cloned_from_title": src["title"],
        "source_context": json.loads(src["context"]) if src.get("context") else None,
        "milestone_template": source_milestones,
        "note": note,
    })

    next_seq = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM initiatives WHERE track = ?", (track,)
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO initiatives (track, seq, title, artifact_url, context, cloned_from_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (track, next_seq, title, src["artifact_url"], context, source_id),
    )
    new_id = cur.lastrowid
    for m_title in source_milestones:
        conn.execute(
            "INSERT INTO initiative_milestones (initiative_id, title, done) VALUES (?, ?, 0)",
            (new_id, m_title),
        )
    return new_id


def list_initiatives(conn, status: str = None, track: str = None) -> list:
    query, params = "SELECT * FROM initiatives", []
    clauses = []
    if status:
        clauses.append("status = ?"); params.append(status)
    if track:
        clauses.append("track = ?"); params.append(track)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY track ASC, seq ASC"
    initiatives = [dict(r) for r in conn.execute(query, params).fetchall()]

    milestone_rows = conn.execute(
        "SELECT * FROM initiative_milestones ORDER BY id ASC"
    ).fetchall()
    by_initiative = {}
    for r in milestone_rows:
        by_initiative.setdefault(r["initiative_id"], []).append(dict(r))

    for init in initiatives:
        milestones = by_initiative.get(init["id"], [])
        done_count = sum(1 for m in milestones if m["done"])
        init["milestones"] = milestones
        init["milestone_total"] = len(milestones)
        init["milestone_done"] = done_count
        init["percent_complete"] = round(100 * done_count / len(milestones)) if milestones else 0
        if init.get("context"):
            try:
                init["context"] = json.loads(init["context"])
            except (TypeError, ValueError):
                # Real corruption found 2026-09-16: id=31 held a plain-text
                # dev note instead of JSON, 500ing this whole endpoint. Don't
                # let one bad row take down the list -- surface it instead.
                init["context"] = {"_malformed": init["context"]}
        else:
            init["context"] = None

    return initiatives


def last_task_for_agent(conn, agent_id: str):
    row = conn.execute(
        "SELECT id, status, created_at FROM tasks WHERE agent_id = ? ORDER BY id DESC LIMIT 1",
        (agent_id,),
    ).fetchone()
    return dict(row) if row else None


def recent_task_count_for_agent(conn, agent_id: str, minutes: int = 30) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE agent_id = ? AND created_at >= datetime('now', ?)",
        (agent_id, f"-{minutes} minutes"),
    ).fetchone()
    return row[0]


# --- Failure Analysis Engine (Task 4) -------------------------------------

def insert_failure_analysis(conn, source_type: str, source_id, title: str, severity: str,
                             summary: str, five_whys: list, root_cause: str,
                             corrective_action: str, preventive_action: str,
                             lessons_learned: str, status: str = "open",
                             agent_id: str = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO failure_analyses (source_type, source_id, title, severity, summary,
                                       five_whys, root_cause, corrective_action,
                                       preventive_action, lessons_learned, status, agent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (source_type, source_id, title, severity, summary, json.dumps(five_whys),
         root_cause, corrective_action, preventive_action, lessons_learned, status, agent_id),
    )
    return cur.lastrowid


def list_failure_analyses(conn, status: str = None, limit: int = 50) -> list:
    query, params = "SELECT * FROM failure_analyses", []
    if status:
        query += " WHERE status = ?"; params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    for r in rows:
        r["five_whys"] = json.loads(r["five_whys"])
    return rows


# --- Dhansetu PeopleDesk (Task 5) ------------------------------------------

def insert_staff(conn, owner_email: str, name: str, role: str, phone: str, pay_type: str,
                  daily_wage_inr, monthly_salary_inr, join_date: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO peopledesk_staff (owner_email, name, role, phone, pay_type,
                                       daily_wage_inr, monthly_salary_inr, join_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (owner_email, name, role, phone, pay_type, daily_wage_inr, monthly_salary_inr, join_date),
    )
    return cur.lastrowid


def list_staff(conn, owner_email: str, status: str = "active") -> list:
    query, params = "SELECT * FROM peopledesk_staff WHERE owner_email = ?", [owner_email]
    if status:
        query += " AND status = ?"; params.append(status)
    query += " ORDER BY name ASC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_staff(conn, staff_id: int):
    row = conn.execute("SELECT * FROM peopledesk_staff WHERE id = ?", (staff_id,)).fetchone()
    return dict(row) if row else None


def set_staff_status(conn, staff_id: int, status: str):
    conn.execute("UPDATE peopledesk_staff SET status = ? WHERE id = ?", (status, staff_id))


def mark_attendance(conn, staff_id: int, attendance_date: str, status: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO peopledesk_attendance (staff_id, attendance_date, status)
        VALUES (?, ?, ?)
        ON CONFLICT(staff_id, attendance_date) DO UPDATE SET status = excluded.status
        """,
        (staff_id, attendance_date, status),
    )
    return cur.lastrowid


def attendance_for_range(conn, owner_email: str, date_from: str, date_to: str) -> list:
    rows = conn.execute(
        """
        SELECT a.* FROM peopledesk_attendance a
        JOIN peopledesk_staff s ON s.id = a.staff_id
        WHERE s.owner_email = ? AND a.attendance_date >= ? AND a.attendance_date <= ?
        ORDER BY a.attendance_date ASC
        """,
        (owner_email, date_from, date_to),
    ).fetchall()
    return [dict(r) for r in rows]


# --- Trading OS (Task 6) ----------------------------------------------------

def insert_strategy(conn, name: str, symbol: str, rule_type: str, params: dict) -> int:
    cur = conn.execute(
        "INSERT INTO trading_strategies (name, symbol, rule_type, params) VALUES (?, ?, ?, ?)",
        (name, symbol, rule_type, json.dumps(params)),
    )
    return cur.lastrowid


def list_strategies(conn, status: str = None) -> list:
    query, params = "SELECT * FROM trading_strategies", []
    if status:
        query += " WHERE status = ?"; params.append(status)
    query += " ORDER BY id ASC"
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    for r in rows:
        r["params"] = json.loads(r["params"])
    return rows


def set_strategy_status(conn, strategy_id: int, status: str):
    conn.execute("UPDATE trading_strategies SET status = ? WHERE id = ?", (status, strategy_id))


def get_open_position(conn, strategy_id: int):
    row = conn.execute(
        "SELECT * FROM paper_positions WHERE strategy_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
        (strategy_id,),
    ).fetchone()
    return dict(row) if row else None


def open_position(conn, strategy_id: int, symbol: str, quantity: float, entry_price: float) -> int:
    cur = conn.execute(
        """
        INSERT INTO paper_positions (strategy_id, symbol, quantity, entry_price)
        VALUES (?, ?, ?, ?)
        """,
        (strategy_id, symbol, quantity, entry_price),
    )
    return cur.lastrowid


def close_position(conn, position_id: int, exit_price: float):
    conn.execute(
        "UPDATE paper_positions SET exit_price = ?, status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (exit_price, position_id),
    )


def list_positions(conn, status: str = None) -> list:
    query, params = "SELECT * FROM paper_positions", []
    if status:
        query += " WHERE status = ?"; params.append(status)
    query += " ORDER BY id DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def insert_journal_entry(conn, position_id: int, strategy_id: int, symbol: str, action: str,
                          quantity: float, price: float, reason: str, pnl: float = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO trading_journal (position_id, strategy_id, symbol, action, quantity, price, pnl, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (position_id, strategy_id, symbol, action, quantity, price, pnl, reason),
    )
    return cur.lastrowid


def list_journal(conn, limit: int = 100) -> list:
    rows = conn.execute(
        "SELECT * FROM trading_journal ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Website Health Watcher ---------------------------------------------

def list_watched_websites(conn, active_only: bool = True) -> list:
    query = "SELECT * FROM watched_websites"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id ASC"
    return [dict(r) for r in conn.execute(query).fetchall()]


def insert_watched_website(conn, url: str, label: str, alert_response_ms_threshold: int = 3000) -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO watched_websites (url, label, alert_response_ms_threshold) VALUES (?, ?, ?)",
        (url, label, alert_response_ms_threshold),
    )
    return cur.lastrowid


def insert_health_check(conn, website_id: int, status: str, status_code: int = None,
                         response_time_ms: int = None, ssl_expires_at: str = None,
                         ssl_days_remaining: int = None, error_detail: str = None) -> int:
    cur = conn.execute(
        """
        INSERT INTO website_health_checks
            (website_id, status, status_code, response_time_ms, ssl_expires_at, ssl_days_remaining, error_detail)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (website_id, status, status_code, response_time_ms, ssl_expires_at, ssl_days_remaining, error_detail),
    )
    return cur.lastrowid


def previous_health_check(conn, website_id: int, before_check_id: int = None):
    """Most recent check for this site, excluding a given check id (used right
    after inserting the new one, to compare against what came before it)."""
    if before_check_id is not None:
        row = conn.execute(
            "SELECT * FROM website_health_checks WHERE website_id = ? AND id < ? ORDER BY id DESC LIMIT 1",
            (website_id, before_check_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM website_health_checks WHERE website_id = ? ORDER BY id DESC LIMIT 1",
            (website_id,),
        ).fetchone()
    return dict(row) if row else None


def latest_health_check(conn, website_id: int):
    row = conn.execute(
        "SELECT * FROM website_health_checks WHERE website_id = ? ORDER BY id DESC LIMIT 1", (website_id,)
    ).fetchone()
    return dict(row) if row else None


def history_health_checks(conn, website_id: int, limit: int = 50) -> list:
    rows = conn.execute(
        "SELECT * FROM website_health_checks WHERE website_id = ? ORDER BY id DESC LIMIT ?",
        (website_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def open_incident(conn, website_id: int) -> int:
    row = conn.execute(
        "SELECT id FROM website_incidents WHERE website_id = ? AND status = 'open' LIMIT 1", (website_id,)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO website_incidents (website_id, status, summary) VALUES (?, 'open', 'Site went offline')",
        (website_id,),
    )
    return cur.lastrowid


def close_open_incident(conn, website_id: int, summary: str) -> None:
    conn.execute(
        """
        UPDATE website_incidents SET status = 'closed', closed_at = CURRENT_TIMESTAMP, summary = ?
        WHERE website_id = ? AND status = 'open'
        """,
        (summary, website_id),
    )


def list_incidents(conn, limit: int = 50) -> list:
    rows = conn.execute(
        "SELECT * FROM website_incidents ORDER BY opened_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- SmartBudget Phase 2 ------------------------------------------------

def insert_income_source(conn, user_id: str, source_name: str, amount: float, frequency: str = "monthly") -> int:
    """Insert a new income source."""
    cur = conn.execute(
        """
        INSERT INTO smartbudget_income_sources (user_id, source_name, amount, frequency)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, source_name, amount, frequency),
    )
    return cur.lastrowid


def get_income_sources(conn, user_id: str) -> list:
    """Get all income sources for a user."""
    rows = conn.execute(
        "SELECT * FROM smartbudget_income_sources WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def insert_expense(conn, user_id: str, category: str, amount: float, date: str, description: str = "", recurring: int = 0) -> int:
    """Insert a new expense."""
    cur = conn.execute(
        """
        INSERT INTO smartbudget_expenses (user_id, category, amount, date, description, recurring)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, category, amount, date, description, recurring),
    )
    return cur.lastrowid


def get_expenses(conn, user_id: str, start_date: str = None, end_date: str = None) -> list:
    """Get expenses for a user, optionally filtered by date range."""
    if start_date and end_date:
        rows = conn.execute(
            """
            SELECT * FROM smartbudget_expenses
            WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY date DESC
            """,
            (user_id, start_date, end_date),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM smartbudget_expenses WHERE user_id = ? ORDER BY date DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_budget(conn, user_id: str, category: str, limit_amount: float, period: str = "month") -> int:
    """Insert or update a budget."""
    # Check if budget exists
    existing = conn.execute(
        "SELECT id FROM smartbudget_budgets WHERE user_id = ? AND category = ?",
        (user_id, category),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE smartbudget_budgets SET limit_amount = ?, period = ? WHERE id = ?",
            (limit_amount, period, existing["id"]),
        )
        return existing["id"]
    else:
        cur = conn.execute(
            """
            INSERT INTO smartbudget_budgets (user_id, category, limit_amount, period)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, category, limit_amount, period),
        )
        return cur.lastrowid


def get_budgets(conn, user_id: str) -> list:
    """Get all budgets for a user."""
    rows = conn.execute(
        "SELECT * FROM smartbudget_budgets WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def insert_transaction(conn, user_id: str, type_: str, amount: float, date: str, description: str = "") -> int:
    """Insert a transaction (income or expense)."""
    cur = conn.execute(
        """
        INSERT INTO smartbudget_transactions (user_id, type, amount, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, type_, amount, date, description),
    )
    return cur.lastrowid


def get_transactions(conn, user_id: str, start_date: str = None, end_date: str = None) -> list:
    """Get transactions for a user, optionally filtered by date range."""
    if start_date and end_date:
        rows = conn.execute(
            """
            SELECT * FROM smartbudget_transactions
            WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY date DESC
            """,
            (user_id, start_date, end_date),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM smartbudget_transactions WHERE user_id = ? ORDER BY date DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_dashboard_summary(conn, user_id: str) -> dict:
    """Get dashboard summary: total income, expenses, net savings, and alerts."""
    # Get current month (ISO format YYYY-MM)
    from datetime import datetime, timedelta
    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")
    month_end = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    month_end = month_end.strftime("%Y-%m-%d")

    # Total income this month
    income_row = conn.execute(
        """
        SELECT SUM(amount) as total FROM smartbudget_income_sources
        WHERE user_id = ? AND created_at >= ?
        """,
        (user_id, month_start),
    ).fetchone()
    total_income = income_row["total"] or 0.0

    # Total expenses this month
    expenses_row = conn.execute(
        """
        SELECT SUM(amount) as total FROM smartbudget_expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
        """,
        (user_id, month_start, month_end),
    ).fetchone()
    total_expenses = expenses_row["total"] or 0.0

    # Budget status per category
    budgets = get_budgets(conn, user_id)
    budget_status = []
    for budget in budgets:
        category_expenses = conn.execute(
            """
            SELECT SUM(amount) as total FROM smartbudget_expenses
            WHERE user_id = ? AND category = ? AND date >= ? AND date <= ?
            """,
            (user_id, budget["category"], month_start, month_end),
        ).fetchone()
        spent = category_expenses["total"] or 0.0
        budget_status.append({
            "category": budget["category"],
            "limit": budget["limit_amount"],
            "spent": spent,
            "percent": (spent / budget["limit_amount"] * 100) if budget["limit_amount"] > 0 else 0,
        })

    # Money leak alerts (spend increase >30% vs previous month)
    previous_month_end = now.replace(day=1) - timedelta(days=1)
    previous_month_start = (now.replace(day=1) - timedelta(days=32)).replace(day=1)
    previous_month_start = previous_month_start.strftime("%Y-%m-%d")
    previous_month_end = previous_month_end.strftime("%Y-%m-%d")

    alerts = []
    categories = conn.execute(
        "SELECT DISTINCT category FROM smartbudget_expenses WHERE user_id = ?",
        (user_id,),
    ).fetchall()

    for cat_row in categories:
        category = cat_row["category"]
        curr_month_expenses = conn.execute(
            """
            SELECT SUM(amount) as total FROM smartbudget_expenses
            WHERE user_id = ? AND category = ? AND date >= ? AND date <= ?
            """,
            (user_id, category, month_start, month_end),
        ).fetchone()["total"] or 0.0

        prev_month_expenses = conn.execute(
            """
            SELECT SUM(amount) as total FROM smartbudget_expenses
            WHERE user_id = ? AND category = ? AND date >= ? AND date <= ?
            """,
            (user_id, category, previous_month_start, previous_month_end),
        ).fetchone()["total"] or 0.0

        if prev_month_expenses > 0:
            percent_increase = ((curr_month_expenses - prev_month_expenses) / prev_month_expenses) * 100
            if percent_increase >= 30:
                alerts.append({
                    "type": "expense_increase",
                    "category": category,
                    "increase_percent": round(percent_increase, 1),
                    "current": round(curr_month_expenses, 2),
                    "previous": round(prev_month_expenses, 2),
                })

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_savings": round(total_income - total_expenses, 2),
        "budget_status": budget_status,
        "alerts": alerts,
    }


# Phase 2 Authentication: Google Sign-In + Session Management
# ============================================================================

def create_or_get_user(conn, email: str, google_id: str, name: str = None, picture_url: str = None):
    """Create or update a user from Google OAuth response.
    
    Returns: user dict with id, email, name, google_id, created_at, last_login_at
    """
    # Check if user exists
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    
    if existing:
        # Update last_login_at for existing user
        conn.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE email = ?",
            (email,)
        )
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    else:
        # Create new user
        conn.execute(
            """
            INSERT INTO users (email, google_id, name, picture_url, last_login_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (email, google_id, name, picture_url)
        )
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    
    return dict(user) if user else None


def create_session(conn, user_id: int, user_email: str, session_id: str, csrf_token: str, expires_at: str):
    """Create a new session for an authenticated user.
    
    Args:
        conn: database connection
        user_id: integer user ID
        user_email: user email address
        session_id: HMAC-SHA256 signed session identifier
        csrf_token: random CSRF protection token
        expires_at: ISO-8601 expiry timestamp
        
    Returns: session dict
    """
    conn.execute(
        """
        INSERT INTO sessions (session_id, user_id, user_email, csrf_token, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, user_id, user_email, csrf_token, expires_at)
    )
    
    session = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    
    return dict(session) if session else None


def get_session(conn, session_id: str):
    """Retrieve a valid, non-expired session.
    
    Returns: session dict or None if expired/invalid
    """
    session = conn.execute(
        """
        SELECT s.*, u.email, u.name 
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_id = ? AND datetime(s.expires_at) > datetime('now')
        """,
        (session_id,)
    ).fetchone()
    
    return dict(session) if session else None


def invalidate_session(conn, session_id: str):
    """Delete a session (logout)."""
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


def cleanup_expired_sessions(conn):
    """Delete all expired sessions (called periodically or on app startup)."""
    conn.execute("DELETE FROM sessions WHERE datetime(expires_at) <= datetime('now')")


def get_user_by_email(conn, email: str):
    """Retrieve user by email address."""
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(user) if user else None


def get_user_by_id(conn, user_id: int):
    """Retrieve user by ID."""
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(user) if user else None
