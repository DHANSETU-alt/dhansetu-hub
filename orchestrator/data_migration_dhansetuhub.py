"""Data migration from workers.dev to dhansetuhub.in production domain."""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class MigrationReport:
    """Track migration progress and results."""
    start_time: str
    end_time: Optional[str] = None
    source_domain: str = "dhansetuhub.workers.dev"
    target_domain: str = "dhansetuhub.in"

    # Database migration
    users_migrated: int = 0
    transactions_migrated: int = 0
    research_records_migrated: int = 0

    # Razorpay migration
    razorpay_payments_migrated: int = 0
    razorpay_refunds_migrated: int = 0

    # Content migration
    articles_migrated: int = 0
    insights_migrated: int = 0

    # Validation results
    database_integrity_checks: list[str] = None
    referential_integrity_errors: list[str] = None

    # Errors encountered
    errors: list[str] = None

    def __post_init__(self):
        if self.database_integrity_checks is None:
            self.database_integrity_checks = []
        if self.referential_integrity_errors is None:
            self.referential_integrity_errors = []
        if self.errors is None:
            self.errors = []

    def mark_complete(self):
        """Mark migration as complete."""
        self.end_time = datetime.now(timezone.utc).isoformat()

    def add_error(self, error: str):
        """Add an error to the migration report."""
        self.errors.append(f"[{datetime.now(timezone.utc).isoformat()}] {error}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class DataMigrator:
    """Handle data migration from workers.dev to dhansetuhub.in."""

    def __init__(self, source_db_path: str, target_db_path: str, dry_run: bool = True):
        """
        Initialize migrator.

        Args:
            source_db_path: Path to source database (workers.dev)
            target_db_path: Path to target database (dhansetuhub.in)
            dry_run: If True, don't commit changes
        """
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
        self.dry_run = dry_run
        self.report = MigrationReport(
            start_time=datetime.now(timezone.utc).isoformat()
        )

    def verify_database_integrity(self, db_path: str) -> bool:
        """
        Verify database integrity before migration.

        Args:
            db_path: Path to database to verify

        Returns:
            True if database is valid, False otherwise
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check database integrity
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            if integrity_result != "ok":
                self.report.add_error(f"Database integrity check failed: {integrity_result}")
                return False

            self.report.database_integrity_checks.append(f"✓ {db_path}: Integrity OK")

            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            fk_errors = cursor.fetchall()

            if fk_errors:
                for error in fk_errors:
                    error_msg = f"Foreign key violation in {error[0]}: {error}"
                    self.report.referential_integrity_errors.append(error_msg)
                    self.report.add_error(error_msg)
                return False

            self.report.database_integrity_checks.append(f"✓ {db_path}: Foreign keys OK")
            conn.close()
            return True

        except Exception as e:
            self.report.add_error(f"Failed to verify database: {str(e)}")
            return False

    def migrate_users(self, conn_source: sqlite3.Connection, conn_target: sqlite3.Connection) -> int:
        """
        Migrate user data from source to target.

        Args:
            conn_source: Source database connection
            conn_target: Target database connection

        Returns:
            Number of users migrated
        """
        try:
            cursor_source = conn_source.cursor()
            cursor_target = conn_target.cursor()

            # Fetch all users from source
            cursor_source.execute("SELECT * FROM users")
            users = cursor_source.fetchall()

            for user in users:
                cursor_target.execute(
                    """INSERT OR REPLACE INTO users
                    (id, username, email, password_hash, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    user
                )

            if not self.dry_run:
                conn_target.commit()

            self.report.users_migrated = len(users)
            return len(users)

        except Exception as e:
            self.report.add_error(f"Failed to migrate users: {str(e)}")
            return 0

    def migrate_razorpay_transactions(
        self, razorpay_data: dict[str, Any]
    ) -> dict[str, int]:
        """
        Migrate Razorpay transaction history.

        Args:
            razorpay_data: Razorpay transactions export

        Returns:
            dict with counts of migrated payments and refunds
        """
        try:
            conn = sqlite3.connect(self.target_db_path)
            cursor = conn.cursor()

            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS razorpay_payments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT DEFAULT 'INR',
                    status TEXT NOT NULL,
                    order_id TEXT,
                    receipt TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS razorpay_refunds (
                    id TEXT PRIMARY KEY,
                    payment_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT DEFAULT 'INR',
                    status TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (payment_id) REFERENCES razorpay_payments(id)
                )
            """)

            payments_migrated = 0
            refunds_migrated = 0

            # Migrate payments
            if "payments" in razorpay_data:
                for payment in razorpay_data["payments"]:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO razorpay_payments
                            (id, user_id, amount, currency, status, order_id, receipt, notes, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            payment.get("id"),
                            payment.get("user_id"),
                            payment.get("amount"),
                            payment.get("currency", "INR"),
                            payment.get("status"),
                            payment.get("order_id"),
                            payment.get("receipt"),
                            json.dumps(payment.get("notes", {})),
                            payment.get("created_at", datetime.now(timezone.utc).isoformat()),
                            datetime.now(timezone.utc).isoformat()
                        ))
                        payments_migrated += 1
                    except Exception as e:
                        self.report.add_error(f"Failed to migrate payment {payment.get('id')}: {str(e)}")

            # Migrate refunds
            if "refunds" in razorpay_data:
                for refund in razorpay_data["refunds"]:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO razorpay_refunds
                            (id, payment_id, user_id, amount, currency, status, notes, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            refund.get("id"),
                            refund.get("payment_id"),
                            refund.get("user_id"),
                            refund.get("amount"),
                            refund.get("currency", "INR"),
                            refund.get("status"),
                            json.dumps(refund.get("notes", {})),
                            refund.get("created_at", datetime.now(timezone.utc).isoformat()),
                            datetime.now(timezone.utc).isoformat()
                        ))
                        refunds_migrated += 1
                    except Exception as e:
                        self.report.add_error(f"Failed to migrate refund {refund.get('id')}: {str(e)}")

            if not self.dry_run:
                conn.commit()

            self.report.razorpay_payments_migrated = payments_migrated
            self.report.razorpay_refunds_migrated = refunds_migrated

            conn.close()
            return {"payments": payments_migrated, "refunds": refunds_migrated}

        except Exception as e:
            self.report.add_error(f"Failed to migrate Razorpay data: {str(e)}")
            return {"payments": 0, "refunds": 0}

    def migrate_research_content(
        self, content_data: dict[str, Any]
    ) -> dict[str, int]:
        """
        Migrate research insights and published content.

        Args:
            content_data: Research content export

        Returns:
            dict with counts of migrated articles and insights
        """
        try:
            conn = sqlite3.connect(self.target_db_path)
            cursor = conn.cursor()

            # Create tables if they don't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_articles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    published_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_insights (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    article_id TEXT NOT NULL,
                    insight TEXT NOT NULL,
                    category TEXT,
                    confidence REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (article_id) REFERENCES research_articles(id)
                )
            """)

            articles_migrated = 0
            insights_migrated = 0

            # Migrate articles
            if "articles" in content_data:
                for article in content_data["articles"]:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO research_articles
                            (id, user_id, title, content, status, published_at, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            article.get("id"),
                            article.get("user_id"),
                            article.get("title"),
                            article.get("content"),
                            article.get("status", "draft"),
                            article.get("published_at"),
                            article.get("created_at", datetime.now(timezone.utc).isoformat()),
                            datetime.now(timezone.utc).isoformat()
                        ))
                        articles_migrated += 1
                    except Exception as e:
                        self.report.add_error(f"Failed to migrate article {article.get('id')}: {str(e)}")

            # Migrate insights
            if "insights" in content_data:
                for insight in content_data["insights"]:
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO research_insights
                            (id, user_id, article_id, insight, category, confidence, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            insight.get("id"),
                            insight.get("user_id"),
                            insight.get("article_id"),
                            insight.get("insight"),
                            insight.get("category"),
                            insight.get("confidence", 0.0),
                            insight.get("created_at", datetime.now(timezone.utc).isoformat()),
                            datetime.now(timezone.utc).isoformat()
                        ))
                        insights_migrated += 1
                    except Exception as e:
                        self.report.add_error(f"Failed to migrate insight {insight.get('id')}: {str(e)}")

            if not self.dry_run:
                conn.commit()

            self.report.articles_migrated = articles_migrated
            self.report.insights_migrated = insights_migrated

            conn.close()
            return {"articles": articles_migrated, "insights": insights_migrated}

        except Exception as e:
            self.report.add_error(f"Failed to migrate research content: {str(e)}")
            return {"articles": 0, "insights": 0}

    def verify_referential_integrity(self, db_path: str) -> bool:
        """
        Verify referential integrity after migration.

        Args:
            db_path: Path to migrated database

        Returns:
            True if all references are valid, False otherwise
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Enable foreign key checks
            cursor.execute("PRAGMA foreign_keys = ON")

            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_key_check")
            errors = cursor.fetchall()

            if errors:
                for error in errors:
                    error_msg = f"Referential integrity error: Table {error[0]}, {error}"
                    self.report.referential_integrity_errors.append(error_msg)
                return False

            self.report.database_integrity_checks.append("✓ Referential integrity verified")
            conn.close()
            return True

        except Exception as e:
            self.report.add_error(f"Failed to verify referential integrity: {str(e)}")
            return False

    def generate_migration_report(self, output_path: str = "migration_report.json"):
        """
        Generate and save migration report.

        Args:
            output_path: Path to save report
        """
        self.report.mark_complete()

        report_dict = self.report.to_dict()

        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)

        print(f"\n=== Migration Report ===")
        print(f"Start: {self.report.start_time}")
        print(f"End: {self.report.end_time}")
        print(f"Duration: {self.report.end_time}")
        print(f"\nUsers Migrated: {self.report.users_migrated}")
        print(f"Razorpay Payments: {self.report.razorpay_payments_migrated}")
        print(f"Razorpay Refunds: {self.report.razorpay_refunds_migrated}")
        print(f"Research Articles: {self.report.articles_migrated}")
        print(f"Research Insights: {self.report.insights_migrated}")
        print(f"\nIntegrity Checks: {len(self.report.database_integrity_checks)}")
        for check in self.report.database_integrity_checks:
            print(f"  {check}")

        if self.report.errors:
            print(f"\nErrors: {len(self.report.errors)}")
            for error in self.report.errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(self.report.errors) > 5:
                print(f"  ... and {len(self.report.errors) - 5} more errors")

        print(f"\nFull report saved to: {output_path}")


def run_migration(
    source_db: str,
    target_db: str,
    razorpay_file: Optional[str] = None,
    content_file: Optional[str] = None,
    dry_run: bool = True,
) -> MigrationReport:
    """
    Run complete data migration.

    Args:
        source_db: Path to source database
        target_db: Path to target database
        razorpay_file: Optional path to Razorpay data JSON export
        content_file: Optional path to content data JSON export
        dry_run: If True, don't commit changes

    Returns:
        MigrationReport with results
    """
    migrator = DataMigrator(source_db, target_db, dry_run=dry_run)

    print("=== Starting Data Migration ===")
    print(f"Source: {source_db}")
    print(f"Target: {target_db}")
    print(f"Dry Run: {dry_run}")
    print()

    # Verify source database
    print("Verifying source database...")
    if not migrator.verify_database_integrity(source_db):
        print("ERROR: Source database integrity check failed")
        return migrator.report

    # Verify target database exists or create
    print("Checking target database...")
    if not Path(target_db).exists():
        print(f"Creating target database: {target_db}")
        conn = sqlite3.connect(target_db)
        conn.close()

    # Migrate user data
    print("Migrating user data...")
    try:
        conn_source = sqlite3.connect(source_db)
        conn_target = sqlite3.connect(target_db)
        migrator.migrate_users(conn_source, conn_target)
        conn_source.close()
        conn_target.close()
    except Exception as e:
        migrator.report.add_error(f"User migration failed: {str(e)}")

    # Migrate Razorpay data
    if razorpay_file and Path(razorpay_file).exists():
        print("Migrating Razorpay transaction history...")
        with open(razorpay_file) as f:
            razorpay_data = json.load(f)
        migrator.migrate_razorpay_transactions(razorpay_data)

    # Migrate research content
    if content_file and Path(content_file).exists():
        print("Migrating research content...")
        with open(content_file) as f:
            content_data = json.load(f)
        migrator.migrate_research_content(content_data)

    # Verify integrity
    print("Verifying referential integrity...")
    migrator.verify_referential_integrity(target_db)

    # Generate report
    migrator.generate_migration_report()

    return migrator.report


if __name__ == "__main__":
    import sys

    source_db = os.environ.get("SOURCE_DB_PATH", "shakthi.db")
    target_db = os.environ.get("TARGET_DB_PATH", "shakthi_dhansetuhub.db")
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"

    report = run_migration(
        source_db=source_db,
        target_db=target_db,
        dry_run=dry_run,
    )

    sys.exit(0 if not report.errors else 1)
