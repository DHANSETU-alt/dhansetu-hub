"""
SHAKTHI Worker Pool -- load balancing decisions. Deterministic, no model
call: "should we scale up" is arithmetic on a real queue depth, not
judgment.

Rule from the mission brief, implemented literally:
  If queue > threshold: assign worker.
  If multiple tasks: parallel execution.
"""
from . import config, db


def get_queue_depth(conn) -> int:
    return db.queue_depth(conn, status="queued")


def should_scale(queue_depth: int, threshold: int = None) -> bool:
    threshold = threshold if threshold is not None else config.WORKER_QUEUE_SCALE_THRESHOLD
    return queue_depth > threshold


def is_queue_overflowing(queue_depth: int) -> bool:
    return queue_depth > config.WORKER_QUEUE_MAX_SIZE


def concurrency_for(worker_type: str, queue_depth: int) -> int:
    """Automatic activation: at/under the scale threshold, each worker
    type runs at its base (usually 1) concurrency -- no reason to spin up
    parallelism for one or two queued tasks. Past the threshold, scale to
    that worker type's configured ceiling (config.WORKER_CONCURRENCY_LIMITS)."""
    base = config.WORKER_BASE_CONCURRENCY
    ceiling = config.WORKER_CONCURRENCY_LIMITS.get(worker_type, base)
    if should_scale(queue_depth):
        return ceiling
    return min(base, ceiling)


def load_balancer_status(conn) -> dict:
    depth = get_queue_depth(conn)
    return {
        "queue_depth": depth,
        "scale_threshold": config.WORKER_QUEUE_SCALE_THRESHOLD,
        "max_queue_size": config.WORKER_QUEUE_MAX_SIZE,
        "scaled_up": should_scale(depth),
        "overflowing": is_queue_overflowing(depth),
        "concurrency": {wt: concurrency_for(wt, depth) for wt in ("rapid", "engineering", "infra")},
    }
