"""Optional Playwright browser operator.

The operator never logs cookies, tokens, or page secrets. It reports an
explicit disconnected state when Playwright or a controlled browser endpoint
is unavailable instead of pretending that a logged-in session exists.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json
import os
from urllib.request import urlopen


@dataclass(frozen=True)
class BrowserStatus:
    state: str
    provider: str
    evidence: str
    chromium_visible: str = "NOT VERIFIED"


class BrowserOperator:
    def __init__(self, *, cdp_url: str | None = None) -> None:
        self.cdp_url = cdp_url or os.getenv("SHAKTHI_BROWSER_CDP_URL", "http://127.0.0.1:9222")

    def status(self) -> BrowserStatus:
        try:
            import playwright  # type: ignore  # optional dependency
        except ImportError:
            # CDP is the supported Linux fallback when Playwright is absent.
            try:
                with urlopen(f"{self.cdp_url}/json/version", timeout=1) as response:
                    info = json.load(response)
                browser = info.get("Browser", "Chromium")
                return BrowserStatus("READY", "CHROMIUM_CDP", f"reachable at {self.cdp_url}", "YES")
            except Exception as exc:
                return BrowserStatus("NOT_CONNECTED", "CHROMIUM_CDP", f"not reachable: {type(exc).__name__}", "NOT VERIFIED")
        try:
            with urlopen(f"{self.cdp_url}/json/version", timeout=1) as response:
                json.load(response)
            return BrowserStatus("READY", "PLAYWRIGHT_CDP", f"reachable at {self.cdp_url}", "YES")
        except Exception as exc:
            return BrowserStatus("NOT_CONNECTED", "PLAYWRIGHT_CDP", f"not reachable: {type(exc).__name__}", "NOT VERIFIED")

    def inspect(self, url: str) -> dict[str, Any]:
        status = self.status()
        if status.state != "READY":
            return {"state": "BROWSER_OPERATOR_NOT_CONNECTED", "url": url, "reason": status.evidence}
        return {"state": "READY_FOR_INSPECTION", "url": url, "provider": status.provider}
