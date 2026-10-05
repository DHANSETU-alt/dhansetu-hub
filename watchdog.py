#!/usr/bin/env python3
"""
24/7 Watchdog — Autonomous system health monitor
Runs continuously, alerts on critical issues
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Critical systems to monitor
MONITORS = {
    "blackboxops.co.in": "https://blackboxops.co.in",
    "dhansetuhub.in": "https://dhansetuhub.in",
    "localhost:3000": "http://localhost:3000",
}

LOG_DIR = Path("/Volumes/DhanSetuSSD/logs")
WATCHDOG_LOG = LOG_DIR / "watchdog.log"

def log_event(level: str, message: str):
    """Log watchdog events to persistent storage."""
    timestamp = datetime.now().isoformat()
    entry = f"[{timestamp}] {level}: {message}"
    print(entry)
    with open(WATCHDOG_LOG, "a") as f:
        f.write(entry + "\n")

def check_site_health(url: str) -> bool:
    """Check if site is responding (basic HTTP 200)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True,
            timeout=5,
            text=True
        )
        return result.stdout.strip() == "200"
    except Exception as e:
        log_event("WARN", f"Health check failed for {url}: {str(e)}")
        return False

def check_ssd_health() -> bool:
    """Verify SSD is still mounted and accessible."""
    ssd_path = Path("/Volumes/DhanSetuSSD")
    return ssd_path.exists() and (ssd_path / "shakthi-db").exists()

def alert(severity: str, message: str):
    """Send alert (critical issues only)."""
    if severity == "CRITICAL":
        log_event("ALERT", f"🚨 CRITICAL: {message}")

def watchdog_loop():
    """Main monitoring loop."""
    log_event("INFO", "Watchdog started — 24/7 monitoring active")

    consecutive_failures = {}

    while True:
        try:
            # Check each critical site
            for name, url in MONITORS.items():
                is_healthy = check_site_health(url)

                if not is_healthy:
                    consecutive_failures[name] = consecutive_failures.get(name, 0) + 1
                    if consecutive_failures[name] == 3:
                        alert("CRITICAL", f"{name} is DOWN (3+ failures)")
                else:
                    if consecutive_failures.get(name, 0) > 0:
                        log_event("RECOVER", f"{name} recovered after {consecutive_failures[name]} failures")
                        consecutive_failures[name] = 0

            # Check SSD health
            if not check_ssd_health():
                alert("CRITICAL", "SSD is not mounted or inaccessible")

            # Sleep before next check (300s = 5 min cycle)
            time.sleep(300)

        except KeyboardInterrupt:
            log_event("INFO", "Watchdog stopping...")
            break
        except Exception as e:
            log_event("ERROR", f"Watchdog error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    watchdog_loop()
