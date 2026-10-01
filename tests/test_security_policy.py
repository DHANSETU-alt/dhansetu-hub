from orchestrator import db
from orchestrator.security_policy import budget_exceeded, normalize_source, prompt_context, redact_secrets


def test_external_input_is_untrusted_and_secrets_are_redacted():
    assert normalize_source("telegram")[1] is False
    assert "external/untrusted" in prompt_context("webpage")[0]
    assert "hunter2" not in redact_secrets("password=hunter2")


def test_task_verification_requires_independent_auditor(tmp_path, monkeypatch):
    monkeypatch.setattr(db.config, "DB_PATH", str(tmp_path / "audit.db"))
    db.init_db()
    with db.get_conn() as conn:
        db.upsert_agent(conn, {
            "id": "worker", "layer": "business", "name": "Worker",
            "default_model_tier": "local", "local_model": "llama3.2",
            "allowed_scope": "single_business", "allowed_tools": "[]",
            "role_prompt": "worker", "squad": "test",
        })
        task_id = db.insert_task(conn, "worker", "test", None, "normal")
        db.update_task(conn, task_id, "done", "claimed output")
        try:
            db.verify_task(conn, task_id, "qa", True, "bad self-check")
            assert False, "self-verification must be rejected"
        except ValueError:
            pass
        db.verify_task(conn, task_id, "auditor", True, "test artifact exists")
        row = conn.execute("SELECT verification_status, verified_by FROM tasks WHERE id = ?", (task_id,)).fetchone()
        assert row[0] == "verified"
        assert row[1] == "auditor"
