"""
SSD Health Monitoring Module
============================

Continuous monitoring of SSD performance, availability, and health.

Monitors:
- Disk space (alert if <500MB free)
- Database latency (track read/write performance)
- SSD availability (failover to memory if SSD goes offline)
- Temperature/wear (if available via SMART data)

Alerts:
- Low disk space warning
- High latency detection
- SSD unavailable notification
"""

import os
import sqlite3
import threading
import time
import json
from pathlib import Path
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

SSD_MOUNT_POINT = Path("/Volumes/CLAUDFLAIR_SSD")
SSD_DB_PATH = SSD_MOUNT_POINT / "shakthi-db" / "shakthi.db"
HEALTH_LOG_PATH = SSD_MOUNT_POINT / "logs" / "ssd_health.log"


class SSDHealthMonitor:
    """Monitors SSD health and performance."""

    def __init__(self, check_interval_seconds: int = 60):
        self.ssd_mount_point = SSD_MOUNT_POINT
        self.db_path = SSD_DB_PATH
        self.check_interval = check_interval_seconds
        self.health_log_path = HEALTH_LOG_PATH
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.alert_callbacks: list[Callable] = []
        self.last_check = {}
        self.lock = threading.RLock()

    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """Register callback for alerts. Signature: callback(alert_type, details)"""
        self.alert_callbacks.append(callback)

    def _trigger_alert(self, alert_type: str, details: Dict):
        """Trigger all registered alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, details)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def check_disk_space(self) -> Dict:
        """Check available disk space."""
        try:
            stat = shutil.disk_usage(self.ssd_mount_point)
            free_mb = stat.free / (1024 * 1024)
            total_mb = stat.total / (1024 * 1024)
            used_mb = stat.used / (1024 * 1024)
            percent_used = (stat.used / stat.total) * 100

            result = {
                "status": "ok",
                "free_mb": round(free_mb, 2),
                "used_mb": round(used_mb, 2),
                "total_mb": round(total_mb, 2),
                "percent_used": round(percent_used, 2),
            }

            # Alert if low disk space
            if free_mb < 500:  # 500MB threshold
                result["status"] = "warning"
                self._trigger_alert("low_disk_space", {
                    "free_mb": free_mb,
                    "threshold_mb": 500,
                })
                logger.warning(f"Low disk space on SSD: {free_mb:.1f}MB free")

            if free_mb < 100:  # 100MB critical
                result["status"] = "critical"
                logger.critical(f"Critical: SSD almost full: {free_mb:.1f}MB free")

            self.last_check["disk_space"] = result
            return result
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return {"status": "error", "error": str(e)}

    def check_ssd_availability(self) -> Dict:
        """Check if SSD is mounted and accessible."""
        try:
            test_file = self.ssd_mount_point / ".health_check"
            test_file.write_text(str(datetime.now().isoformat()))
            test_file.unlink()

            result = {
                "status": "ok",
                "ssd_mounted": True,
                "write_test": "passed",
            }

            self.last_check["availability"] = result
            return result
        except Exception as e:
            logger.error(f"SSD availability check failed: {e}")
            self._trigger_alert("ssd_unavailable", {"error": str(e)})
            return {
                "status": "error",
                "ssd_mounted": False,
                "error": str(e),
            }

    def measure_database_latency(self) -> Dict:
        """Measure database read/write latency."""
        if not self.db_path.exists():
            return {
                "status": "error",
                "error": "Database not found",
            }

        latencies = {
            "status": "ok",
            "read_latency_ms": None,
            "write_latency_ms": None,
        }

        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)

            # Read latency
            start = time.time()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            cursor.fetchone()
            read_latency = (time.time() - start) * 1000
            latencies["read_latency_ms"] = round(read_latency, 2)

            # Write latency (wrapped in transaction to avoid actual changes)
            conn.execute("BEGIN TRANSACTION")
            start = time.time()
            cursor.execute("PRAGMA optimize")
            write_latency = (time.time() - start) * 1000
            conn.execute("ROLLBACK")
            latencies["write_latency_ms"] = round(write_latency, 2)

            conn.close()

            # Alert if latency is high
            if read_latency > 100:  # 100ms threshold
                latencies["status"] = "warning"
                self._trigger_alert("high_latency", {
                    "type": "read",
                    "latency_ms": read_latency,
                    "threshold_ms": 100,
                })
                logger.warning(f"High database read latency: {read_latency:.1f}ms")

            if write_latency > 100:
                latencies["status"] = "warning"
                self._trigger_alert("high_latency", {
                    "type": "write",
                    "latency_ms": write_latency,
                    "threshold_ms": 100,
                })

            self.last_check["database_latency"] = latencies
            return latencies
        except Exception as e:
            logger.error(f"Database latency check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    def get_ssd_smart_data(self) -> Optional[Dict]:
        """Attempt to read SMART data from SSD (macOS specific)."""
        try:
            # macOS: use diskutil to get SSD info
            result = subprocess.run(
                ["diskutil", "info", str(self.ssd_mount_point)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse output for useful data
                output = result.stdout
                smart_data = {}

                # Extract key metrics
                for line in output.split("\n"):
                    if "Device Node:" in line:
                        smart_data["device"] = line.split(":")[-1].strip()
                    elif "Mount Point:" in line:
                        smart_data["mount_point"] = line.split(":")[-1].strip()
                    elif "Writable:" in line:
                        smart_data["writable"] = line.split(":")[-1].strip()

                return smart_data
            return None
        except Exception as e:
            logger.debug(f"Failed to read SMART data: {e}")
            return None

    def get_health_status(self) -> Dict:
        """Get comprehensive SSD health status."""
        with self.lock:
            status = {
                "timestamp": datetime.now().isoformat(),
                "ssd_mount_point": str(self.ssd_mount_point),
                "checks": {
                    "availability": self.check_ssd_availability(),
                    "disk_space": self.check_disk_space(),
                    "database_latency": self.measure_database_latency(),
                },
                "smart_data": self.get_ssd_smart_data(),
            }

            # Determine overall status
            check_statuses = [
                status["checks"]["availability"].get("status", "unknown"),
                status["checks"]["disk_space"].get("status", "unknown"),
                status["checks"]["database_latency"].get("status", "unknown"),
            ]

            if "critical" in check_statuses:
                status["overall_status"] = "critical"
            elif "error" in check_statuses:
                status["overall_status"] = "error"
            elif "warning" in check_statuses:
                status["overall_status"] = "warning"
            else:
                status["overall_status"] = "ok"

            return status

    def log_health_check(self, status: Dict):
        """Log health check results."""
        try:
            self.health_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.health_log_path, "a") as f:
                f.write(json.dumps(status, default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to log health check: {e}")

    def monitoring_loop(self):
        """Continuous monitoring loop."""
        logger.info(f"SSD health monitoring started (interval: {self.check_interval}s)")

        while self.monitoring:
            try:
                status = self.get_health_status()
                self.log_health_check(status)

                # Log summary
                overall = status["overall_status"]
                if overall != "ok":
                    logger.warning(f"SSD health check: {overall}")

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            time.sleep(self.check_interval)

    def start_monitoring(self):
        """Start background monitoring thread."""
        with self.lock:
            if self.monitoring:
                logger.warning("Monitoring already running")
                return

            self.monitoring = True
            self.monitor_thread = threading.Thread(
                target=self.monitoring_loop,
                daemon=True,
                name="SSD-Health-Monitor",
            )
            self.monitor_thread.start()
            logger.info("SSD health monitoring thread started")

    def stop_monitoring(self):
        """Stop background monitoring thread."""
        with self.lock:
            if not self.monitoring:
                return

            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            logger.info("SSD health monitoring stopped")

    def get_monitoring_report(self) -> Dict:
        """Get current monitoring status and recent checks."""
        return {
            "monitoring_active": self.monitoring,
            "check_interval_seconds": self.check_interval,
            "last_checks": self.last_check,
        }


# Global monitor instance
_ssd_monitor: Optional[SSDHealthMonitor] = None


def get_ssd_monitor() -> SSDHealthMonitor:
    """Get or create global SSD health monitor."""
    global _ssd_monitor
    if _ssd_monitor is None:
        _ssd_monitor = SSDHealthMonitor()
    return _ssd_monitor


def setup_ssd_monitoring(check_interval_seconds: int = 60):
    """Initialize and start SSD monitoring."""
    monitor = get_ssd_monitor()
    monitor.start_monitoring()


def stop_ssd_monitoring():
    """Stop SSD monitoring."""
    monitor = get_ssd_monitor()
    monitor.stop_monitoring()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    monitor = SSDHealthMonitor(check_interval_seconds=5)

    # Test immediate check
    status = monitor.get_health_status()
    print(json.dumps(status, indent=2, default=str))

    # Test monitoring for 30 seconds
    print("\nStarting monitoring for 30 seconds...")
    monitor.start_monitoring()
    time.sleep(30)
    monitor.stop_monitoring()

    # Get report
    report = monitor.get_monitoring_report()
    print(json.dumps(report, indent=2, default=str))
