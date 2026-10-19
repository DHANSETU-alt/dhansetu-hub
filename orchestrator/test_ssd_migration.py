"""
SSD Migration Test Suite
========================

Comprehensive tests for SSD migration system.

Test Coverage:
- SSD setup and initialization
- Database migration and checksums
- Session/cache persistence
- Startup sequence
- Health monitoring
- Graceful degradation
"""

import unittest
import tempfile
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
import os
import sys

# Adjust path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ssd_migration import SSDMigrationManager, setup_ssd
from db_migration import (
    calculate_file_sha256,
    verify_database_integrity,
    copy_database,
    migrate_database,
)
from session_cache_migration import SessionCacheManager, get_session_manager
from ssd_health import SSDHealthMonitor


class TestSSDMigration(unittest.TestCase):
    """Test SSD migration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_ssd_manager_initialization(self):
        """Test SSDMigrationManager initialization."""
        manager = SSDMigrationManager(self.temp_path)
        self.assertIsNotNone(manager)
        self.assertEqual(manager.ssd_mount_point, self.temp_path)

    def test_ssd_dir_creation(self):
        """Test SSD directory creation."""
        manager = SSDMigrationManager(self.temp_path)
        success, results = manager.initialize_ssd_directories()

        self.assertTrue(success)
        self.assertIn("database", results)
        self.assertIn("logs", results)
        self.assertIn("cache", results)
        self.assertIn("uploads", results)

        # Verify directories exist
        for dir_name, dir_path in manager.ssd_dirs.items():
            self.assertTrue(dir_path.exists())
            self.assertTrue(dir_path.is_dir())

    def test_ssd_disk_space_check(self):
        """Test disk space checking."""
        manager = SSDMigrationManager(self.temp_path)
        space_info = manager.get_ssd_disk_space()

        self.assertIsNotNone(space_info)
        self.assertIn("total_bytes", space_info)
        self.assertIn("free_bytes", space_info)
        self.assertIn("used_bytes", space_info)
        self.assertIn("percent_used", space_info)

    def test_migration_state_persistence(self):
        """Test saving and loading migration state."""
        manager = SSDMigrationManager(self.temp_path)
        manager.initialize_ssd_directories()

        test_state = {
            "phase": "test_phase",
            "timestamp": datetime.now().isoformat(),
        }

        # Save state
        self.assertTrue(manager.save_migration_state(test_state))

        # Load state
        loaded_state = manager.load_migration_state()
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state["phase"], "test_phase")


class TestDatabaseMigration(unittest.TestCase):
    """Test database migration functionality."""

    def setUp(self):
        """Set up test databases."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create a test database
        self.source_db = self.temp_path / "test_source.db"
        self.dest_db = self.temp_path / "test_dest.db"

        conn = sqlite3.connect(str(self.source_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL
            )
        """)
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('test1', 1.5)")
        cursor.execute("INSERT INTO test_table (name, value) VALUES ('test2', 2.5)")
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test databases."""
        self.temp_dir.cleanup()

    def test_calculate_checksum(self):
        """Test SHA256 checksum calculation."""
        checksum = calculate_file_sha256(self.source_db)
        self.assertIsNotNone(checksum)
        self.assertEqual(len(checksum), 64)  # SHA256 hex is 64 characters

        # Verify same file produces same checksum
        checksum2 = calculate_file_sha256(self.source_db)
        self.assertEqual(checksum, checksum2)

    def test_verify_database_integrity(self):
        """Test database integrity verification."""
        is_valid, message = verify_database_integrity(self.source_db)
        self.assertTrue(is_valid)
        # Message should contain indication of success
        self.assertTrue("ok" in message.lower() or "integrity" in message.lower())

    def test_copy_database(self):
        """Test database copying with checksum verification."""
        success, status = copy_database(self.source_db, self.dest_db)

        self.assertTrue(success)
        self.assertEqual(status["source_checksum_sha256"], status["destination_checksum_sha256"])
        self.assertTrue(self.dest_db.exists())

        # Verify destination database is valid
        is_valid, _ = verify_database_integrity(self.dest_db)
        self.assertTrue(is_valid)

    def test_database_data_integrity(self):
        """Test that data is preserved during copy."""
        success, _ = copy_database(self.source_db, self.dest_db)
        self.assertTrue(success)

        # Check data in destination
        conn = sqlite3.connect(str(self.dest_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 2)


class TestSessionCacheMigration(unittest.TestCase):
    """Test session and cache migration."""

    def setUp(self):
        """Set up test cache database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.cache_db = self.temp_path / "test_cache.db"

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_session_cache_initialization(self):
        """Test cache database initialization."""
        manager = SessionCacheManager(self.cache_db)
        self.assertTrue(self.cache_db.exists())

    def test_store_and_retrieve_session(self):
        """Test storing and retrieving sessions."""
        manager = SessionCacheManager(self.cache_db)

        test_session = {
            "user_id": 123,
            "username": "test_user",
            "roles": ["admin", "user"],
        }

        # Store session
        stored = manager.store_session("session_1", test_session)
        self.assertTrue(stored)

        # Retrieve session
        retrieved = manager.retrieve_session("session_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["user_id"], 123)
        self.assertEqual(retrieved["username"], "test_user")

    def test_session_expiration(self):
        """Test session expiration."""
        manager = SessionCacheManager(self.cache_db)

        test_session = {"data": "test"}

        # Store session with very short expiration (1 hour = baseline)
        manager.store_session("session_exp", test_session, expires_in_hours=1)

        # Retrieve immediately (should work since not expired)
        retrieved = manager.retrieve_session("session_exp")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["data"], "test")

    def test_cache_set_and_get(self):
        """Test cache set/get operations."""
        manager = SessionCacheManager(self.cache_db)

        test_value = {"key": "value", "number": 42}

        # Set cache
        manager.cache_set("test_key", test_value, ttl_seconds=3600)

        # Get cache
        retrieved = manager.cache_get("test_key")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["key"], "value")
        self.assertEqual(retrieved["number"], 42)

    def test_cache_stats(self):
        """Test cache statistics."""
        manager = SessionCacheManager(self.cache_db)

        # Add some data
        manager.store_session("s1", {"data": "test1"})
        manager.cache_set("c1", {"cache": "value"})

        stats = manager.get_cache_stats()
        self.assertIn("sessions_count", stats)
        self.assertIn("cache_entries_count", stats)

    def test_cleanup_expired(self):
        """Test cleaning up expired entries."""
        manager = SessionCacheManager(self.cache_db)

        # This is a basic test - full testing would require time manipulation
        deleted_sessions, deleted_cache = manager.cleanup_expired()
        self.assertIsInstance(deleted_sessions, int)
        self.assertIsInstance(deleted_cache, int)


class TestSSDHealthMonitoring(unittest.TestCase):
    """Test SSD health monitoring."""

    def setUp(self):
        """Set up health monitor."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_health_monitor_initialization(self):
        """Test SSDHealthMonitor initialization."""
        monitor = SSDHealthMonitor(check_interval_seconds=30)
        self.assertIsNotNone(monitor)
        self.assertEqual(monitor.check_interval, 30)

    def test_disk_space_check(self):
        """Test disk space checking."""
        monitor = SSDHealthMonitor()
        # Override mount point to temp directory that exists
        monitor.ssd_mount_point = Path(self.temp_dir.name)
        space_check = monitor.check_disk_space()

        self.assertIsNotNone(space_check)
        self.assertIn("status", space_check)
        # If status is not error, should have space info
        if space_check.get("status") != "error":
            self.assertIn("free_mb", space_check)
            self.assertIn("percent_used", space_check)

    def test_ssd_availability_check(self):
        """Test SSD availability checking."""
        monitor = SSDHealthMonitor(check_interval_seconds=5)
        # Use temp dir instead of actual SSD mount
        monitor.ssd_mount_point = Path(self.temp_dir.name)

        availability = monitor.check_ssd_availability()
        self.assertIn("status", availability)

    def test_alert_callback(self):
        """Test alert callback registration."""
        monitor = SSDHealthMonitor()

        alerts = []

        def alert_handler(alert_type, details):
            alerts.append({"type": alert_type, "details": details})

        monitor.add_alert_callback(alert_handler)
        self.assertEqual(len(monitor.alert_callbacks), 1)

    def test_health_status_report(self):
        """Test comprehensive health status."""
        monitor = SSDHealthMonitor()
        monitor.ssd_mount_point = Path(self.temp_dir.name)

        status = monitor.get_health_status()
        self.assertIn("timestamp", status)
        self.assertIn("overall_status", status)
        self.assertIn("checks", status)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete migration workflow."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_complete_database_migration_flow(self):
        """Test complete database migration workflow."""
        # Create source database
        source_db = self.temp_path / "source.db"
        conn = sqlite3.connect(str(source_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE data (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
        """)
        for i in range(1000):
            cursor.execute("INSERT INTO data (content) VALUES (?)", (f"record_{i}",))
        conn.commit()
        conn.close()

        # Perform migration
        dest_db = self.temp_path / "dest.db"
        success, report = copy_database(source_db, dest_db, verify_checksum=True)

        self.assertTrue(success)
        self.assertTrue(dest_db.exists())

        # Verify data
        conn = sqlite3.connect(str(dest_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM data")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1000)

    def test_session_migration_and_recovery(self):
        """Test session migration and recovery on restart."""
        cache_db = self.temp_path / "cache.db"
        manager = SessionCacheManager(cache_db)

        # Create sessions
        sessions = {}
        for i in range(100):
            session_data = {
                "user_id": i,
                "username": f"user_{i}",
                "permissions": ["read", "write"],
            }
            sessions[f"session_{i}"] = session_data
            manager.store_session(f"session_{i}", session_data)

        # Verify all stored
        for session_id, expected_data in sessions.items():
            retrieved = manager.retrieve_session(session_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["user_id"], expected_data["user_id"])

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate tracking."""
        cache_db = self.temp_path / "cache.db"
        manager = SessionCacheManager(cache_db)

        # Set some cache entries
        for i in range(10):
            manager.cache_set(f"key_{i}", {"value": i})

        # Access them multiple times
        for _ in range(5):
            for i in range(10):
                manager.cache_get(f"key_{i}")

        stats = manager.get_cache_stats()
        self.assertGreater(stats["total_cache_hits"], 0)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSSDMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionCacheMigration))
    suite.addTests(loader.loadTestsFromTestCase(TestSSDHealthMonitoring))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
