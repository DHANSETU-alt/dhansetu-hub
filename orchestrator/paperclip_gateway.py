"""Optional Paperclip reachability probe; it does not imply agents are active."""

import os
import urllib.error
import urllib.request


def status(timeout: float = 1.5) -> str:
    """Return service reachability, never a fabricated agent/heartbeat state."""
    base_url = os.environ.get("PAPERCLIP_API_URL", "").rstrip("/")
    if not base_url:
        return "not configured (set PAPERCLIP_API_URL)"
    request = urllib.request.Request(f"{base_url}/api/health", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return "reachable" if 200 <= response.status < 300 else f"unhealthy (HTTP {response.status})"
    except (OSError, urllib.error.URLError, TimeoutError):
        return "unavailable"

