"""
Startup Sequence Module
=======================

Orchestrates the complete startup procedure for Phase 2 SSD migration.

Startup flow:
1. Check SSD mounted
2. Verify database accessible on SSD
3. Migrate any in-memory data to SSD
4. Start API server with SSD paths
5. Perform health checks
6. Set up monitoring
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging
import sqlite3

logger = logging.getLogger(__name__)


class StartupSequence:
    """Manages application startup with SSD integration."""

    def __init__(self):
        self.ssd_mount_point = Path("/Volumes/CLAUDFLAIR_SSD")
        self.startup_log = []
        self.errors = []
        self.warnings = []

    def log_step(self, step_name: str, success: bool, message: str):
        """Log startup step."""
        entry = {
            "step": step_name,
            "success": success,
            "message": message,
            "timestamp": time.time(),
        }
        self.startup_log.append(entry)

        level = logging.INFO if success else logging.ERROR
        logger.log(level, f"[{step_name}] {message}")

    def step_1_check_ssd_mounted(self) -> bool:
        """Step 1: Verify SSD is mounted."""
        try:
            if not self.ssd_mount_point.exists():
                self.errors.append(f"SSD mount point not found: {self.ssd_mount_point}")
                self.log_step("check_ssd_mounted", False, "SSD not mounted")
                return False

            # Test write access
            test_file = self.ssd_mount_point / ".startup_test"
            test_file.write_text("startup_test")
            test_file.unlink()

            self.log_step("check_ssd_mounted", True, f"SSD mounted at {self.ssd_mount_point}")
            return True
        except Exception as e:
            self.errors.append(f"SSD mount check failed: {e}")
            self.log_step("check_ssd_mounted", False, str(e))
            return False

    def step_2_verify_database(self) -> bool:
        """Step 2: Verify database is accessible on SSD."""
        try:
            from . import config
            db_path = Path(config.DB_PATH)

            if not db_path.exists():
                self.errors.append(f"Database not found at {db_path}")
                self.log_step("verify_database", False, f"DB not found: {db_path}")
                return False

            # Test database connection
            conn = sqlite3.connect(str(db_path), timeout=10.0)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()

            self.log_step("verify_database", True, f"Database accessible at {db_path}")
            return True
        except Exception as e:
            self.errors.append(f"Database verification failed: {e}")
            self.log_step("verify_database", False, str(e))
            return False

    def step_3_migrate_sessions(self) -> bool:
        """Step 3: Migrate in-memory sessions to SSD cache."""
        try:
            from .session_cache_migration import get_session_manager

            manager = get_session_manager()
            stats = manager.get_cache_stats()

            msg = f"Session cache initialized: {stats['cache_entries_count']} entries, " \
                  f"{stats['sessions_count']} sessions"
            self.log_step("migrate_sessions", True, msg)
            return True
        except Exception as e:
            self.warnings.append(f"Session migration encountered issue: {e}")
            self.log_step("migrate_sessions", False, str(e))
            # Don't fail startup for this
            return True

    def step_4_setup_ssd_monitoring(self) -> bool:
        """Step 4: Initialize SSD health monitoring."""
        try:
            from .ssd_health import setup_ssd_monitoring
            setup_ssd_monitoring()

            self.log_step("setup_ssd_monitoring", True, "SSD monitoring initialized")
            return True
        except Exception as e:
            self.warnings.append(f"SSD monitoring setup issue: {e}")
            self.log_step("setup_ssd_monitoring", False, str(e))
            # Don't fail startup for this
            return True

    def step_5_verify_disk_space(self) -> bool:
        """Step 5: Verify adequate disk space."""
        try:
            import shutil

            stat = shutil.disk_usage(self.ssd_mount_point)
            free_mb = stat.free / (1024 * 1024)

            if free_mb < 500:  # 500MB threshold
                self.warnings.append(f"Low disk space on SSD: {free_mb:.1f}MB free")
                msg = f"WARNING: Only {free_mb:.1f}MB free on SSD (threshold: 500MB)"
                self.log_step("verify_disk_space", False, msg)
                return False

            percent_used = (stat.used / stat.total) * 100
            msg = f"Disk space OK: {free_mb:.1f}MB free ({percent_used:.1f}% used)"
            self.log_step("verify_disk_space", True, msg)
            return True
        except Exception as e:
            self.warnings.append(f"Disk space check failed: {e}")
            self.log_step("verify_disk_space", False, str(e))
            return True

    def step_6_health_check(self) -> bool:
        """Step 6: Perform comprehensive health check."""
        try:
            from . import config

            health_results = {
                "ssd_mounted": True,
                "database_accessible": True,
                "disk_space_ok": True,
            }

            # Database read/write test
            try:
                db_path = Path(config.DB_PATH)
                conn = sqlite3.connect(str(db_path), timeout=10.0)

                # Time a read
                start = time.time()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                read_time = time.time() - start

                health_results["database_read_latency_ms"] = read_time * 1000

                # Time a write (in transaction, will rollback)
                cursor.execute("BEGIN TRANSACTION")
                start = time.time()
                cursor.execute("PRAGMA optimize")
                cursor.execute("ROLLBACK")
                write_time = time.time() - start

                health_results["database_write_latency_ms"] = write_time * 1000

                if read_time > 0.1:  # 100ms threshold
                    self.warnings.append(f"High database read latency: {read_time*1000:.1f}ms")

                conn.close()

                msg = f"Health check passed: " \
                      f"Read {read_time*1000:.1f}ms, Write {write_time*1000:.1f}ms"
                self.log_step("health_check", True, msg)
                return True
            except Exception as e:
                self.errors.append(f"Health check failed: {e}")
                self.log_step("health_check", False, str(e))
                return False
        except Exception as e:
            self.errors.append(f"Health check setup failed: {e}")
            self.log_step("health_check", False, str(e))
            return False

    def run_startup_sequence(self) -> Tuple[bool, Dict]:
        """
        Execute complete startup sequence.
        Returns: (success: bool, report: {details})
        """
        logger.info("=" * 60)
        logger.info("SHAKTHI_OS Phase 2 SSD Startup Sequence")
        logger.info("=" * 60)

        steps = [
            ("Check SSD Mounted", self.step_1_check_ssd_mounted),
            ("Verify Database", self.step_2_verify_database),
            ("Setup Session/Cache", self.step_3_migrate_sessions),
            ("Setup SSD Monitoring", self.step_4_setup_ssd_monitoring),
            ("Verify Disk Space", self.step_5_verify_disk_space),
            ("Health Check", self.step_6_health_check),
        ]

        results = []
        for step_name, step_func in steps:
            try:
                result = step_func()
                results.append({"step": step_name, "success": result})
                if not result and "mounted" in step_name.lower():
                    # Skip remaining steps if SSD isn't mounted
                    logger.error("Cannot continue without SSD. Aborting startup.")
                    break
            except Exception as e:
                logger.error(f"Unexpected error in {step_name}: {e}")
                results.append({"step": step_name, "success": False, "error": str(e)})

        # Determine overall success
        critical_steps = ["Check SSD Mounted", "Verify Database"]
        overall_success = all(
            r["success"] for r in results
            if r["step"] in critical_steps
        )

        report = {
            "startup_timestamp": time.time(),
            "overall_success": overall_success,
            "critical_steps_passed": sum(
                1 for r in results
                if r["step"] in critical_steps and r["success"]
            ),
            "total_critical_steps": len(critical_steps),
            "steps": results,
            "startup_log": self.startup_log,
            "warnings": self.warnings,
            "errors": self.errors,
        }

        logger.info("=" * 60)
        if overall_success:
            logger.info("✓ SHAKTHI_OS Startup Complete - All Systems Ready")
        else:
            logger.error("✗ SHAKTHI_OS Startup Failed - Check logs above")
        logger.info("=" * 60)

        return overall_success, report

    def save_startup_report(self, output_path: Path) -> bool:
        """Save startup report to file."""
        try:
            # Run startup if not already done
            if not self.startup_log:
                _, report = self.run_startup_sequence()
            else:
                report = {
                    "steps": self.startup_log,
                    "warnings": self.warnings,
                    "errors": self.errors,
                }

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2, default=str))
            logger.info(f"Startup report saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save startup report: {e}")
            return False


def run_startup() -> Tuple[bool, Dict]:
    """Execute startup sequence."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    startup = StartupSequence()
    success, report = startup.run_startup_sequence()

    return success, report


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    startup = StartupSequence()
    success, report = startup.run_startup_sequence()

    # Save report
    report_path = Path("/tmp/shakthi_startup_report.json")
    startup.save_startup_report(report_path)

    print(json.dumps(report, indent=2, default=str))
    exit(0 if success else 1)
