"""Bounded, optional Hindsight status bridge for the local control plane.

This module deliberately does not invent memory availability: without an
explicit endpoint it reports disabled, and network failures are unavailable.
Credentials are never logged or returned.
"""

import os
import urllib.error
import urllib.request


def _base_url() -> str:
    return os.environ.get("HINDSIGHT_API_URL", "http://127.0.0.1:8888").rstrip("/")


def status(timeout: float = 1.5) -> str:
    """Return a dashboard-safe status string for the optional memory service."""
    if not os.environ.get("HINDSIGHT_API_URL"):
        return "not configured (set HINDSIGHT_API_URL)"
    request = urllib.request.Request(f"{_base_url()}/health", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return "reachable" if 200 <= response.status < 300 else f"unhealthy (HTTP {response.status})"
    except (OSError, urllib.error.URLError, TimeoutError):
        return "unavailable"

