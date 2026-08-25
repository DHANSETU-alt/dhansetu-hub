"""
SHAKTHI Worker Pool -- the execution engine.

Real parallel execution via concurrent.futures.ThreadPoolExecutor -- the
right tool here since every worker task is I/O-bound (an HTTP call to
Ollama/a website, a subprocess call to Node for a browser audit), not
CPU-bound; threads release the GIL during I/O waits, so this gets real
concurrency, not simulated.

SQLite constraint, stated plainly: this file is single-writer under the
hood. Each worker thread opens its OWN connection (db.get_conn() is
always called fresh, per-thread, never shared or passed across threads --
sqlite3 connections aren't safe to share that way). db._connect() now
sets a 30s busy_timeout specifically for this reason. "rapid" and "infra"
tasks never hold a connection open across a slow call, so they're safe at
high concurrency; "engineering" tasks (see worker_registry.py) sometimes
do (correction_review holds one across a local model call) -- concurrency
for that type is kept modest (config.WORKER_CONCURRENCY_LIMITS) as a real
mitigation, not just a number picked at random.

Workers do not make business decisions -- every dispatched function
already existed before this file (chrome_developer.review_website,
security.security_posture_scan, ...); this only adds parallelism and
queueing on top.
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from . import config, db, load_manager, worker_registry

GLOBAL_MAX_CONCURRENCY = 8


def ensure_workers_registered():
    """Idempotent -- registers concurrency_limit worker rows per type
    (rapid-1..rapid-8, engineering-1..engineering-3, infra-1..infra-4) so
    the dashboard's 'Active Workers' reflects real, distinct instances,
    not just a type label."""
    with db.get_conn() as conn:
        for worker_type in worker_registry.WORKER_TYPES:
            limit = config.WORKER_CONCURRENCY_LIMITS.get(worker_type, 1)
            for i in range(1, limit + 1):
                db.upsert_worker(conn, f"{worker_type}-{i}", worker_type, limit)


def enqueue_task(kind: str, payload: dict, priority: int = 5) -> int:
    worker_registry.worker_type_for_kind(kind)  # raises ValueError early if kind is unknown
    with db.get_conn() as conn:
        return db.enqueue_work(conn, kind, json.dumps(payload), priority)


def _pick_worker(conn, worker_type: str) -> dict:
    """Prefers an idle worker of the right type; falls back to the
    least-recently-active one if all are currently marked busy -- 'busy'
    here is a status label for the dashboard, not a hard mutex (the
    ThreadPoolExecutor's max_workers is the real concurrency limit)."""
    rows = [w for w in db.list_workers(conn) if w["worker_type"] == worker_type]
    idle = [w for w in rows if w["status"] == "idle"]
    if idle:
        return idle[0]
    rows.sort(key=lambda w: w["last_active_at"] or "")
    return rows[0]


def _execute_one(work_item: dict) -> dict:
    kind = work_item["kind"]
    worker_type = worker_registry.worker_type_for_kind(kind)
    payload = json.loads(work_item["payload"] or "{}")

    with db.get_conn() as conn:
        worker = _pick_worker(conn, worker_type)
        db.mark_worker_busy(conn, worker["id"])
        db.mark_work_running(conn, work_item["id"], worker_type, worker["id"])

    try:
        result = worker_registry.run_task(kind, payload)
        with db.get_conn() as conn:
            db.complete_work(conn, work_item["id"], json.dumps(result, default=str))
            db.mark_worker_idle(conn, worker["id"], succeeded=True)
        return {"id": work_item["id"], "kind": kind, "ok": True}
    except Exception as e:
        with db.get_conn() as conn:
            db.fail_work(conn, work_item["id"], str(e))
            db.mark_worker_failed(conn, worker["id"])
        return {"id": work_item["id"], "kind": kind, "ok": False, "error": str(e)}


def drain_queue(max_workers: int = None, telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    """Pulls all currently-queued work, dispatches it through the pool in
    parallel, and reports what happened. One pass, not a loop -- see
    run_worker_daemon() for continuous operation."""
    ensure_workers_registered()

    with db.get_conn() as conn:
        status = load_manager.load_balancer_status(conn)
        batch = db.next_queued_work(conn, limit=status["queue_depth"] or 0)

    if not batch:
        return {"dispatched": 0, "succeeded": 0, "failed": 0, "load_balancer": status}

    if max_workers is None:
        relevant_types = {worker_registry.worker_type_for_kind(item["kind"]) for item in batch}
        max_workers = min(GLOBAL_MAX_CONCURRENCY, len(batch),
                           sum(load_manager.concurrency_for(t, status["queue_depth"]) for t in relevant_types))
    max_workers = max(1, max_workers)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_execute_one, item) for item in batch]
        for f in as_completed(futures):
            results.append(f.result())

    succeeded = sum(1 for r in results if r["ok"])
    failed = [r for r in results if not r["ok"]]

    _send_alerts(status, failed, telegram_token, telegram_chat_id)

    return {"dispatched": len(results), "succeeded": succeeded, "failed": len(failed),
            "failures": failed, "max_workers_used": max_workers, "load_balancer": status}


def _send_alerts(status: dict, failed: list, telegram_token: str, telegram_chat_id: str):
    if not (failed or status["overflowing"]):
        return
    from . import sentinel, telegram as tg, telegram_service as ts
    try:
        token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
    except tg.TelegramError:
        return

    messages = []
    if failed:
        messages.append(f"⚠️ Worker failure: {len(failed)} task(s) failed — " +
                         "; ".join(f"#{r['id']} ({r['kind']}): {r['error'][:60]}" for r in failed[:5]))
    if status["overflowing"]:
        messages.append(f"🚨 Queue overflow: {status['queue_depth']} queued, over the {status['max_queue_size']} limit")

    health = sentinel.collect_health()
    if status["overflowing"] and (health.get("cpu_percent") or 0) > 85 and (health.get("ram_percent") or 0) > 85:
        messages.append(f"🚨 Critical resource usage under worker load: CPU {health['cpu_percent']}% RAM {health['ram_percent']}%")

    if messages:
        try:
            tg.send_message(token, chat_id, "🧵 SHAKTHI WORKER POOL ALERT\n\n" + "\n".join(messages), parse_mode=None)
        except tg.TelegramError:
            pass


def run_worker_daemon(interval_seconds: int, telegram_token: str = None, telegram_chat_id: str = None):
    """Continuous loop -- same pattern as sentinel_loop: foreground,
    Ctrl+C to stop, run under a background shell/launchd for real
    continuous operation. This is what makes 'workers automatically
    activate when workloads increase' actually continuous rather than
    only reacting when someone happens to run --worker-drain."""
    import time
    print(f"Worker daemon: draining every {interval_seconds}s (Ctrl+C to stop)...")
    while True:
        result = drain_queue(telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)
        if result["dispatched"]:
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] dispatched={result['dispatched']} "
                  f"succeeded={result['succeeded']} failed={result['failed']} "
                  f"queue_depth={result['load_balancer']['queue_depth']} scaled_up={result['load_balancer']['scaled_up']}")
        time.sleep(interval_seconds)
