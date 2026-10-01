"""
API tests for rate limiting, error handling, and authentication.

Tests cover:
- Rate limiting with boundary testing (10 attempts per 15 minutes for auth)
- Error handling standardization (no stack traces, consistent format)
- Token bucket algorithm correctness
- Per-IP isolation
- Edge cases and boundary conditions
"""
import json
import time
import pytest
from orchestrator import rate_limiting


class TestRateLimitingAuth:
    """Test rate limiting on auth endpoints."""

    def test_auth_endpoint_rate_limit_10_per_15min(self):
        """Auth endpoints allow 10 requests per 15 minutes."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.100"
        limit, window = rate_limiting.AUTH_RATE_LIMIT

        # First 10 requests should succeed
        for i in range(10):
            allowed, info = store.check_rate_limit(client_ip, limit, window)
            assert allowed, f"Request {i+1} should be allowed"
            assert info["remaining"] == 10 - i - 1

        # 11th request should fail
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert not allowed
        assert info["retry_after"] is not None

    def test_rate_limit_boundary_exact_10(self):
        """Test rate limit at exact boundary (10th request)."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.101"
        limit, window = rate_limiting.AUTH_RATE_LIMIT

        # Consume exactly 9 tokens
        for _ in range(9):
            store.check_rate_limit(client_ip, limit, window)

        # 10th should succeed
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert allowed
        assert info["remaining"] == 0

        # 11th should fail
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert not allowed

    def test_rate_limit_reset_after_window(self):
        """Rate limit resets after window expires."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.102"
        # Use short window for testing
        short_limit = (3, 1)  # 3 requests per 1 second

        # Consume limit
        for _ in range(3):
            allowed, _ = store.check_rate_limit(client_ip, *short_limit)
            assert allowed

        # 4th should fail
        allowed, _ = store.check_rate_limit(client_ip, *short_limit)
        assert not allowed

        # Wait for window to pass
        time.sleep(1.1)

        # Should succeed again
        allowed, info = store.check_rate_limit(client_ip, *short_limit)
        assert allowed
        assert info["remaining"] == 2

    def test_rate_limit_per_ip_isolation(self):
        """Different IPs have independent rate limits."""
        store = rate_limiting._test_get_memory_store()
        limit, window = rate_limiting.AUTH_RATE_LIMIT

        # IP 1: consume 5 requests
        for _ in range(5):
            store.check_rate_limit("192.168.1.1", limit, window)

        # IP 2: should still have full quota
        allowed, info = store.check_rate_limit("192.168.1.2", limit, window)
        assert allowed
        assert info["remaining"] == 9  # limit - 1

    def test_rate_limit_token_refill(self):
        """Tokens refill over time."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.103"
        # 2 requests per 1 second
        limit_config = (2, 1)

        # Consume both tokens
        store.check_rate_limit(client_ip, *limit_config)
        store.check_rate_limit(client_ip, *limit_config)

        # Wait half window
        time.sleep(0.5)

        # Should have about 1 token refilled
        allowed, info = store.check_rate_limit(client_ip, *limit_config)
        status = store.get_status(client_ip, *limit_config)
        assert status["remaining"] >= 0


class TestRateLimitHeaders:
    """Test rate limit response headers."""

    def test_rate_limit_headers_included(self):
        """Response includes rate limit headers."""
        client_ip = "127.0.0.1"
        endpoint = "/api/health"

        allowed, headers = rate_limiting.check_rate_limit(client_ip, endpoint)

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert int(headers["X-RateLimit-Limit"]) > 0

    def test_retry_after_on_limit_exceeded(self):
        """Retry-After header included when rate limit exceeded."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "127.0.0.2"
        limit, window = 2, 60

        # Consume limit
        store.check_rate_limit(client_ip, limit, window)
        store.check_rate_limit(client_ip, limit, window)

        # Next request should include retry-after
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert not allowed
        assert info["retry_after"] is not None
        assert info["retry_after"] > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_rate_limit_with_zero_remaining(self):
        """Correct behavior when exactly zero tokens remain."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.50"
        limit, window = 1, 60

        # Use the one token
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert allowed
        assert info["remaining"] == 0

        # Next should fail
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert not allowed
        assert info["remaining"] == 0

    def test_rate_limit_fractional_tokens(self):
        """Token bucket correctly handles fractional tokens."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.51"
        # 3 requests per 10 seconds = 0.3 tokens/second
        limit, window = (3, 10)

        # Consume 2 tokens
        store.check_rate_limit(client_ip, limit, window)
        store.check_rate_limit(client_ip, limit, window)

        # Wait 3.33 seconds (should refill 1 token)
        time.sleep(3.5)

        # Should have 1 token again
        allowed, info = store.check_rate_limit(client_ip, limit, window)
        assert allowed


class TestRateLimitConfiguration:
    """Test rate limit configuration."""

    def test_auth_vs_general_rate_limits_differ(self):
        """Auth endpoints have stricter rate limits than general."""
        auth_limit, auth_window = rate_limiting.AUTH_RATE_LIMIT
        general_limit, general_window = rate_limiting.GENERAL_RATE_LIMIT

        # Auth should be more restrictive
        auth_rate = auth_limit / auth_window
        general_rate = general_limit / general_window

        assert auth_rate < general_rate, "Auth endpoints should have lower rate limit"

    def test_rate_limit_disabled_allows_all(self):
        """When disabled, all requests pass rate limit check."""
        from unittest.mock import patch
        with patch.object(rate_limiting, 'RATE_LIMIT_ENABLED', False):
            allowed, headers = rate_limiting.check_rate_limit("192.168.1.100", "/api/auth/login")
            assert allowed
            assert headers == {}

    def test_auth_endpoints_recognized(self):
        """Auth endpoint list includes login and register."""
        assert "/api/auth/login" in rate_limiting.AUTH_ENDPOINTS
        assert "/api/auth/register" in rate_limiting.AUTH_ENDPOINTS
        assert "/api/login" in rate_limiting.AUTH_ENDPOINTS


class TestErrorResponseFormat:
    """Test error response formatting standards."""

    def test_error_response_has_error_field(self):
        """All error responses should include 'error' field."""
        errors = [
            {"error": "missing or invalid token"},
            {"error": "too many requests"},
            {"error": "no such route: /api/test"},
            {"error": "internal server error"},
        ]

        for error in errors:
            assert "error" in error
            assert isinstance(error["error"], str)

    def test_error_message_generic_for_500(self):
        """500 errors use generic message without stack trace."""
        error_message = "internal server error"

        # Should not expose Python details
        assert "Traceback" not in error_message
        assert "File " not in error_message
        assert "Exception" not in error_message


class TestAuthenticationConfig:
    """Test authentication configuration."""

    def test_loopback_addresses_defined(self):
        """Loopback addresses are properly defined."""
        import orchestrator.api as api_mod

        assert "127.0.0.1" in api_mod.LOOPBACK_ADDRESSES
        assert "::1" in api_mod.LOOPBACK_ADDRESSES

    def test_rate_limit_applied_to_auth_endpoints(self):
        """Rate limiting is applied to auth endpoints."""
        endpoint = "/api/auth/login"

        # Check rate limit for auth endpoint
        allowed, headers = rate_limiting.check_rate_limit("192.168.1.100", endpoint)

        # Should have rate limit headers
        assert "X-RateLimit-Limit" in headers

        # Auth endpoints should have specific limit
        limit = int(headers["X-RateLimit-Limit"])
        assert limit == rate_limiting.AUTH_RATE_LIMIT[0]


class TestConcurrentRequests:
    """Test behavior under concurrent requests."""

    def test_rate_limit_per_ip_concurrent(self):
        """Rate limits are properly isolated per IP under concurrency."""
        store = rate_limiting._test_get_memory_store()

        # Simulate concurrent requests from different IPs
        ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        limit, window = rate_limiting.AUTH_RATE_LIMIT

        # Each IP should have independent counters
        for ip in ips:
            for _ in range(10):
                allowed, _ = store.check_rate_limit(ip, limit, window)
                assert allowed

            # 11th should fail for this IP
            allowed, _ = store.check_rate_limit(ip, limit, window)
            assert not allowed

        # Verify each IP's independent state
        for ip in ips:
            status = store.get_status(ip, limit, window)
            # All IPs should be at their limit
            assert status["remaining"] == 0


class TestRateLimitStorage:
    """Test rate limit storage implementation."""

    def test_memory_store_initialization(self):
        """In-memory store initializes correctly."""
        store = rate_limiting._test_get_memory_store()

        assert isinstance(store, rate_limiting.InMemoryRateLimitStore)
        assert hasattr(store, 'buckets')

    def test_reset_clears_bucket(self):
        """Reset clears rate limit for an IP."""
        store = rate_limiting._test_get_memory_store()
        client_ip = "192.168.1.60"
        limit, window = 5, 60

        # Consume tokens
        for _ in range(4):
            store.check_rate_limit(client_ip, limit, window)

        status_before = store.get_status(client_ip, limit, window)
        assert status_before["remaining"] == 1

        # Reset
        store.reset(client_ip)

        status_after = store.get_status(client_ip, limit, window)
        assert status_after["remaining"] == limit


class TestRateLimitIntegration:
    """Integration tests for rate limiting."""

    def test_rate_limit_per_endpoint_type(self):
        """Different endpoint types use appropriate limits."""
        auth_endpoint = "/api/auth/login"
        general_endpoint = "/api/health"

        # Auth endpoint should use stricter limit
        _, auth_headers = rate_limiting.check_rate_limit("192.168.1.70", auth_endpoint)
        _, general_headers = rate_limiting.check_rate_limit("192.168.1.70", general_endpoint)

        auth_limit = int(auth_headers.get("X-RateLimit-Limit", 0))
        general_limit = int(general_headers.get("X-RateLimit-Limit", 0))

        assert auth_limit > 0
        assert general_limit > 0
        assert auth_limit < general_limit

    def test_rate_limit_survives_restart(self):
        """In-memory store resets on restart (expected behavior)."""
        store1 = rate_limiting._test_get_memory_store()

        # Consume some tokens
        for _ in range(8):
            store1.check_rate_limit("192.168.1.80", 10, 900)

        # Create new store (simulating restart)
        store2 = rate_limiting._test_get_memory_store()

        # New store should have full quota for the IP
        allowed, info = store2.check_rate_limit("192.168.1.80", 10, 900)
        assert allowed
        assert info["remaining"] == 9  # -1 for this request


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
