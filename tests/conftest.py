"""
Pytest configuration and fixtures for payment integration tests.
"""
import pytest
from orchestrator import db


@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """Initialize the database before running tests."""
    db.init_db()
    yield
    # Cleanup could go here if needed


@pytest.fixture(autouse=True)
def cleanup_payment_transactions():
    """Clean up payment_transactions before each test to avoid UNIQUE constraint issues."""
    # Clear payment transactions before each test
    with db.get_conn() as conn:
        conn.execute("DELETE FROM payment_transactions")
    yield
    # Cleanup after test is optional
