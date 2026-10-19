"""
Session & Cache Migration Module
=================================

Handles migration of in-memory session store and cache to SSD-backed storage.

Architecture:
- Primary: SQLite cache on SSD (persistent, fast)
- Fallback: Memory cache (if SSD unavailable)
- Redis optional layer (future enhancement)

Features:
- Migrate active sessions from memory to SSD
- Initialize persistent cache layer
- Graceful degradation if SSD unavailable
- Session recovery on restart
"""

import sqlite3
import json
import pickle
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import threading

logger = logging.getLogger(__name__)

SSD_MOUNT_POINT = Path("/Volumes/CLAUDFLAIR_SSD")
CACHE_DB_PATH = SSD_MOUNT_POINT / "cache" / "session_cache.db"


class SessionCacheManager:
    """Manages persistent session and cache storage on SSD."""

    def __init__(self, db_path: Path = CACHE_DB_PATH):
        self.db_path = db_path
        self.memory_cache: Dict[str, Dict[str, Any]] = {}  # Fallback in-memory cache
        self.lock = threading.RLock()  # Thread-safe operations
        self._initialize_cache_db()

    def _initialize_cache_db(self) -> bool:
        """Initialize SQLite cache database schema."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()

            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    metadata TEXT
                )
            """)

            # Cache entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    ttl_seconds INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    hit_count INTEGER DEFAULT 0
                )
            """)

            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)")

            conn.commit()
            conn.close()
            logger.info(f"Cache database initialized at {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {e}")
            return False

    def _is_ssd_available(self) -> bool:
        """Check if SSD is mounted and writable."""
        try:
            test_file = self.db_path.parent / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Get database connection with error handling."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect to cache database: {e}")
            return None

    def store_session(
        self,
        session_id: str,
        session_data: Dict[str, Any],
        expires_in_hours: int = 24,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Store session data persistently on SSD."""
        with self.lock:
            # Try SSD first
            if self._is_ssd_available():
                try:
                    conn = self._get_connection()
                    if conn:
                        cursor = conn.cursor()
                        expires_at = datetime.now() + timedelta(hours=expires_in_hours)

                        cursor.execute("""
                            INSERT OR REPLACE INTO sessions
                            (session_id, data, accessed_at, expires_at, metadata)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            session_id,
                            pickle.dumps(session_data),
                            datetime.now(),
                            expires_at,
                            json.dumps(metadata or {}),
                        ))
                        conn.commit()
                        conn.close()
                        logger.debug(f"Session {session_id} stored on SSD")
                        return True
                except Exception as e:
                    logger.warning(f"Failed to store session on SSD: {e}")

            # Fallback to memory
            self.memory_cache[session_id] = {
                "data": session_data,
                "expires_at": datetime.now() + timedelta(hours=expires_in_hours),
                "metadata": metadata or {},
            }
            logger.debug(f"Session {session_id} stored in memory (fallback)")
            return True

    def retrieve_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data from SSD or memory."""
        with self.lock:
            # Try SSD first
            if self._is_ssd_available():
                try:
                    conn = self._get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT data, expires_at FROM sessions
                            WHERE session_id = ?
                        """, (session_id,))

                        row = cursor.fetchone()
                        conn.close()

                        if row:
                            data, expires_at = row[0], row[1]
                            expires_at = datetime.fromisoformat(expires_at)

                            # Check expiration
                            if expires_at > datetime.now():
                                return pickle.loads(data)
                            else:
                                # Session expired, clean it up
                                self.delete_session(session_id)
                except Exception as e:
                    logger.warning(f"Failed to retrieve session from SSD: {e}")

            # Fallback to memory
            if session_id in self.memory_cache:
                session = self.memory_cache[session_id]
                if session["expires_at"] > datetime.now():
                    return session["data"]
                else:
                    del self.memory_cache[session_id]

            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session from SSD and memory."""
        with self.lock:
            deleted = False

            # Delete from SSD
            if self._is_ssd_available():
                try:
                    conn = self._get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                        conn.commit()
                        conn.close()
                        deleted = True
                except Exception as e:
                    logger.warning(f"Failed to delete session from SSD: {e}")

            # Delete from memory
            if session_id in self.memory_cache:
                del self.memory_cache[session_id]
                deleted = True

            return deleted

    def cache_set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> bool:
        """Store value in cache with TTL."""
        with self.lock:
            # Try SSD first
            if self._is_ssd_available():
                try:
                    conn = self._get_connection()
                    if conn:
                        cursor = conn.cursor()
                        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

                        cursor.execute("""
                            INSERT OR REPLACE INTO cache_entries
                            (key, value, ttl_seconds, expires_at)
                            VALUES (?, ?, ?, ?)
                        """, (
                            key,
                            pickle.dumps(value),
                            ttl_seconds,
                            expires_at,
                        ))
                        conn.commit()
                        conn.close()
                        logger.debug(f"Cache entry {key} stored on SSD")
                        return True
                except Exception as e:
                    logger.warning(f"Failed to store cache on SSD: {e}")

            # Fallback: store in memory dict (no TTL enforcement, just basic cache)
            self.memory_cache[f"cache:{key}"] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl_seconds),
            }
            return True

    def cache_get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        with self.lock:
            # Try SSD first
            if self._is_ssd_available():
                try:
                    conn = self._get_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT value, expires_at, hit_count FROM cache_entries
                            WHERE key = ?
                        """, (key,))

                        row = cursor.fetchone()

                        if row:
                            value, expires_at, hit_count = row[0], row[1], row[2]
                            expires_at = datetime.fromisoformat(expires_at)

                            # Check expiration
                            if expires_at > datetime.now():
                                # Update hit count
                                cursor.execute("""
                                    UPDATE cache_entries SET hit_count = hit_count + 1
                                    WHERE key = ?
                                """, (key,))
                                conn.commit()
                                conn.close()
                                return pickle.loads(value)
                            else:
                                # Expired, clean up
                                cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                                conn.commit()
                                conn.close()
                        else:
                            conn.close()
                except Exception as e:
                    logger.warning(f"Failed to retrieve cache from SSD: {e}")

            # Fallback to memory
            cache_key = f"cache:{key}"
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                if entry["expires_at"] > datetime.now():
                    return entry["value"]
                else:
                    del self.memory_cache[cache_key]

            return None

    def cleanup_expired(self) -> Tuple[int, int]:
        """
        Remove expired sessions and cache entries.
        Returns: (deleted_sessions, deleted_cache_entries)
        """
        with self.lock:
            deleted_sessions = 0
            deleted_cache = 0

            if self._is_ssd_available():
                try:
                    conn = self._get_connection()
                    if conn:
                        cursor = conn.cursor()

                        # Clean up expired sessions
                        cursor.execute("""
                            DELETE FROM sessions
                            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
                        """)
                        deleted_sessions = cursor.rowcount

                        # Clean up expired cache
                        cursor.execute("""
                            DELETE FROM cache_entries
                            WHERE expires_at < datetime('now')
                        """)
                        deleted_cache = cursor.rowcount

                        conn.commit()
                        conn.close()

                        if deleted_sessions > 0 or deleted_cache > 0:
                            logger.info(
                                f"Cleaned up {deleted_sessions} sessions, "
                                f"{deleted_cache} cache entries"
                            )
                except Exception as e:
                    logger.warning(f"Failed to cleanup expired entries: {e}")

            return deleted_sessions, deleted_cache

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache database statistics."""
        stats = {
            "ssd_available": self._is_ssd_available(),
            "memory_cache_size": len(self.memory_cache),
        }

        if self._is_ssd_available():
            try:
                conn = self._get_connection()
                if conn:
                    cursor = conn.cursor()

                    cursor.execute("SELECT COUNT(*) FROM sessions")
                    stats["sessions_count"] = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM cache_entries")
                    stats["cache_entries_count"] = cursor.fetchone()[0]

                    cursor.execute("SELECT SUM(hit_count) FROM cache_entries")
                    stats["total_cache_hits"] = cursor.fetchone()[0] or 0

                    cursor.execute("""
                        SELECT COUNT(*) FROM cache_entries
                        WHERE expires_at > datetime('now')
                    """)
                    stats["valid_cache_entries"] = cursor.fetchone()[0]

                    conn.close()
            except Exception as e:
                logger.warning(f"Failed to get cache stats: {e}")

        return stats

    def migrate_from_memory(self, memory_sessions: Dict[str, Dict]) -> Tuple[int, int]:
        """
        Migrate sessions from in-memory store to SSD.
        Returns: (migrated_count, failed_count)
        """
        migrated = 0
        failed = 0

        for session_id, session_data in memory_sessions.items():
            try:
                if self.store_session(session_id, session_data):
                    migrated += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to migrate session {session_id}: {e}")
                failed += 1

        logger.info(f"Session migration: {migrated} successful, {failed} failed")
        return migrated, failed


# Global session manager instance
_session_manager: Optional[SessionCacheManager] = None


def get_session_manager() -> SessionCacheManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionCacheManager()
    return _session_manager


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    manager = get_session_manager()

    # Test session storage
    test_session = {"user_id": 123, "username": "test_user"}
    manager.store_session("test_session_123", test_session)

    # Test retrieval
    retrieved = manager.retrieve_session("test_session_123")
    print(f"Stored and retrieved: {retrieved}")

    # Test cache
    manager.cache_set("test_key", {"data": "value"}, ttl_seconds=3600)
    cached = manager.cache_get("test_key")
    print(f"Cached and retrieved: {cached}")

    # Get stats
    stats = manager.get_cache_stats()
    print(f"Cache stats: {json.dumps(stats, indent=2)}")
