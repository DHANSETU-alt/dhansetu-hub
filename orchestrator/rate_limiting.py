"""
Rate limiting module for API endpoints.

Implements token bucket algorithm with per-IP tracking for auth endpoints.
Uses in-memory store with optional Redis fallback.

Config:
- RATE_LIMIT_ENABLED: Enable/disable globally (default: True)
- RATE_LIMIT_STORAGE: 'memory' or 'redis' (default: 'memory')
- RATE_LIMIT_REDIS_URL: Redis connection string (if using redis)
"""
import time
import json
from collections import defaultdict
from typing import Optional, Tuple
import os

# Configuration
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_STORAGE = os.environ.get("RATE_LIMIT_STORAGE", "memory")
RATE_LIMIT_REDIS_URL = os.environ.get("RATE_LIMIT_REDIS_URL")

# Rate limit config: (requests_per_window, window_seconds)
# Auth endpoints: 10 requests per 15 minutes
AUTH_RATE_LIMIT = (10, 900)  # 10 attempts per 15 minutes
GENERAL_RATE_LIMIT = (100, 60)  # 100 requests per minute (default)

# Endpoints requiring strict rate limiting
AUTH_ENDPOINTS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/login",
    "/api/register",
}


class RateLimitStore:
    """Abstract base for rate limit storage backends."""

    def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, dict]:
        """Check if request is within rate limit.

        Args:
            key: Identifier (e.g., IP address or user ID)
            limit: Number of allowed requests
            window: Time window in seconds

        Returns:
            Tuple of (allowed: bool, info: dict with limit metadata)
        """
        raise NotImplementedError

    def get_status(self, key: str, limit: int, window: int) -> dict:
        """Get current rate limit status for a key."""
        raise NotImplementedError

    def reset(self, key: str) -> None:
        """Reset rate limit counter for a key."""
        raise NotImplementedError


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit store using token bucket algorithm."""

    def __init__(self):
        # Store: {key: {"tokens": float, "last_update": float}}
        self.buckets = defaultdict(lambda: {"tokens": None, "last_update": None})
        self.lock_warning_issued = False

    def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, dict]:
        """Check rate limit using token bucket algorithm."""
        now = time.time()
        bucket = self.buckets[key]

        # Initialize bucket on first request
        if bucket["tokens"] is None:
            bucket["tokens"] = float(limit)
            bucket["last_update"] = now

        # Refill tokens based on elapsed time
        elapsed = now - bucket["last_update"]
        refill_rate = limit / window  # tokens per second
        bucket["tokens"] = min(limit, bucket["tokens"] + elapsed * refill_rate)
        bucket["last_update"] = now

        # Check if request is allowed
        remaining = bucket["tokens"]
        allowed = remaining >= 1.0

        if allowed:
            bucket["tokens"] -= 1.0

        # Calculate retry_after for when limit is hit
        retry_after = None
        if not allowed:
            # Time until we have 1 token again
            retry_after = int((1.0 - bucket["tokens"]) / refill_rate) + 1

        info = {
            "limit": limit,
            "window_seconds": window,
            "remaining": max(0, int(bucket["tokens"])),
            "reset_seconds": int(window - elapsed) if allowed else retry_after,
            "retry_after": retry_after,
        }

        return allowed, info

    def get_status(self, key: str, limit: int, window: int) -> dict:
        """Get rate limit status without consuming tokens."""
        now = time.time()
        bucket = self.buckets[key]

        if bucket["tokens"] is None:
            return {
                "limit": limit,
                "window_seconds": window,
                "remaining": limit,
                "reset_seconds": window,
                "retry_after": None,
            }

        elapsed = now - bucket["last_update"]
        refill_rate = limit / window
        current_tokens = min(limit, bucket["tokens"] + elapsed * refill_rate)

        return {
            "limit": limit,
            "window_seconds": window,
            "remaining": max(0, int(current_tokens)),
            "reset_seconds": int(window - elapsed),
            "retry_after": None,
        }

    def reset(self, key: str) -> None:
        """Reset rate limit counter."""
        self.buckets[key] = {"tokens": None, "last_update": None}


class RedisRateLimitStore(RateLimitStore):
    """Rate limit store using Redis backend."""

    def __init__(self, redis_url: str):
        try:
            import redis
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")

    def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, dict]:
        """Check rate limit using Redis."""
        redis_key = f"rate_limit:{key}"
        now = time.time()

        try:
            # Use Lua script for atomic operation
            script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])

            local bucket = redis.call('HGETALL', key)
            local tokens = limit
            local last_update = now

            if #bucket > 0 then
                tokens = tonumber(bucket[2])
                last_update = tonumber(bucket[4])
            end

            local elapsed = now - last_update
            local refill_rate = limit / window
            tokens = math.min(limit, tokens + elapsed * refill_rate)

            local allowed = tokens >= 1
            if allowed then
                tokens = tokens - 1
            end

            redis.call('HSET', key, 'tokens', tokens, 'last_update', now)
            redis.call('EXPIRE', key, window)

            return {allowed and 1 or 0, math.max(0, math.floor(tokens)), limit, window}
            """

            result = self.redis.eval(script, 1, redis_key, limit, window, now)
            allowed = result[0] == 1
            remaining = result[1]

            retry_after = None
            if not allowed:
                retry_after = int((1.0 - remaining) / (limit / window)) + 1

            info = {
                "limit": limit,
                "window_seconds": window,
                "remaining": remaining,
                "reset_seconds": window,
                "retry_after": retry_after,
            }

            return allowed, info
        except Exception as e:
            # Fall back to allowing request if Redis fails
            return True, {
                "limit": limit,
                "window_seconds": window,
                "remaining": limit,
                "reset_seconds": window,
                "retry_after": None,
                "error": f"Redis error: {str(e)}",
            }

    def get_status(self, key: str, limit: int, window: int) -> dict:
        """Get rate limit status from Redis."""
        redis_key = f"rate_limit:{key}"
        try:
            bucket = self.redis.hgetall(redis_key)
            if not bucket:
                return {
                    "limit": limit,
                    "window_seconds": window,
                    "remaining": limit,
                    "reset_seconds": window,
                    "retry_after": None,
                }

            tokens = float(bucket.get("tokens", limit))
            return {
                "limit": limit,
                "window_seconds": window,
                "remaining": max(0, int(tokens)),
                "reset_seconds": window,
                "retry_after": None,
            }
        except Exception as e:
            return {
                "limit": limit,
                "window_seconds": window,
                "remaining": limit,
                "reset_seconds": window,
                "retry_after": None,
                "error": f"Redis error: {str(e)}",
            }

    def reset(self, key: str) -> None:
        """Reset rate limit in Redis."""
        redis_key = f"rate_limit:{key}"
        self.redis.delete(redis_key)


# Global store instance
_store: Optional[RateLimitStore] = None


def get_store() -> RateLimitStore:
    """Get or initialize the rate limit store."""
    global _store
    if _store is None:
        if RATE_LIMIT_STORAGE == "redis" and RATE_LIMIT_REDIS_URL:
            _store = RedisRateLimitStore(RATE_LIMIT_REDIS_URL)
        else:
            _store = InMemoryRateLimitStore()
    return _store


def check_rate_limit(
    client_ip: str,
    endpoint: str,
    custom_limit: Optional[Tuple[int, int]] = None,
) -> Tuple[bool, dict]:
    """Check if a request is within rate limits.

    Args:
        client_ip: Client IP address
        endpoint: API endpoint path
        custom_limit: Optional (limit, window) tuple to override defaults

    Returns:
        Tuple of (allowed: bool, headers: dict with rate limit info)
    """
    if not RATE_LIMIT_ENABLED:
        return True, {}

    # Determine rate limit
    if custom_limit:
        limit, window = custom_limit
    elif endpoint in AUTH_ENDPOINTS:
        limit, window = AUTH_RATE_LIMIT
    else:
        limit, window = GENERAL_RATE_LIMIT

    # Check rate limit
    store = get_store()
    allowed, info = store.check_rate_limit(client_ip, limit, window)

    # Build response headers
    headers = {
        "X-RateLimit-Limit": str(info["limit"]),
        "X-RateLimit-Remaining": str(info["remaining"]),
        "X-RateLimit-Reset": str(int(time.time()) + info.get("reset_seconds", 0)),
    }

    if info.get("retry_after"):
        headers["Retry-After"] = str(info["retry_after"])

    return allowed, headers


def get_rate_limit_status(
    client_ip: str,
    endpoint: str,
    custom_limit: Optional[Tuple[int, int]] = None,
) -> dict:
    """Get current rate limit status for a client."""
    if not RATE_LIMIT_ENABLED:
        return {"enabled": False}

    # Determine rate limit
    if custom_limit:
        limit, window = custom_limit
    elif endpoint in AUTH_ENDPOINTS:
        limit, window = AUTH_RATE_LIMIT
    else:
        limit, window = GENERAL_RATE_LIMIT

    store = get_store()
    status = store.get_status(client_ip, limit, window)
    status["enabled"] = True
    return status


def reset_rate_limit(client_ip: str) -> None:
    """Reset rate limit for a client (admin only)."""
    store = get_store()
    store.reset(client_ip)


# Test fixtures
def _test_get_memory_store() -> InMemoryRateLimitStore:
    """Get in-memory store for testing."""
    return InMemoryRateLimitStore()
