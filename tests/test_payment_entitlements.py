import tempfile
import unittest
from pathlib import Path

from orchestrator import db, pricing


class PaymentEntitlementTest(unittest.TestCase):
    def setUp(self):
        self.original_db = db.config.DB_PATH
        self.temp_dir = tempfile.TemporaryDirectory(prefix="dhansetu_payment_test_")
        db.config.DB_PATH = str(Path(self.temp_dir.name) / "payments.db")
        db.init_db()

    def tearDown(self):
        db.config.DB_PATH = self.original_db
        self.temp_dir.cleanup()

    def create_order(self):
        with db.get_conn() as conn:
            db.insert_payment_transaction(
                conn, gateway="razorpay_order", gateway_ref="order_123", amount=149,
                currency="INR", description="smartbudget_pro",
                customer_contact=" Customer@Example.COM ", status="created",
            )

    def test_verified_payment_grants_one_lifetime_entitlement(self):
        self.create_order()
        first = pricing.reconcile_order_payment("order_123", "paid", payment_id="pay_123")
        second = pricing.reconcile_order_payment("order_123", "paid", payment_id="pay_123")

        self.assertEqual(first["entitlement_status"], "active")
        self.assertEqual(second["subscription_id"], first["subscription_id"])
        with db.get_conn() as conn:
            subscriptions = db.list_subscriptions(conn, product="smartbudget_pro")
            transaction = db.get_payment_transaction(conn, "order_123")
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0]["email"], "customer@example.com")
        self.assertIsNone(subscriptions[0]["valid_until"])
        self.assertEqual(transaction["status"], "paid")
        self.assertEqual(transaction["payment_id"], "pay_123")

    def test_failed_event_cannot_downgrade_paid_order(self):
        self.create_order()
        pricing.reconcile_order_payment("order_123", "paid", payment_id="pay_123")
        result = pricing.reconcile_order_payment("order_123", "failed", payment_id="pay_123")

        self.assertEqual(result["transaction_status"], "paid")
        self.assertEqual(result["outcome"], "ignored_stale_failure")

    def test_refund_revokes_entitlement_idempotently(self):
        self.create_order()
        pricing.reconcile_order_payment("order_123", "paid", payment_id="pay_123")
        first = pricing.reconcile_order_payment("order_123", "refunded", payment_id="pay_123")
        second = pricing.reconcile_order_payment("order_123", "refunded", payment_id="pay_123")

        self.assertEqual(first["entitlement_status"], "cancelled")
        self.assertEqual(second["subscription_id"], first["subscription_id"])
        with db.get_conn() as conn:
            subscriptions = db.list_subscriptions(conn, product="smartbudget_pro")
            transaction = db.get_payment_transaction(conn, "order_123")
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0]["status"], "cancelled")
        self.assertEqual(transaction["status"], "refunded")

    def test_payment_without_customer_identity_does_not_grant_access(self):
        with db.get_conn() as conn:
            db.insert_payment_transaction(
                conn, gateway="razorpay_order", gateway_ref="order_no_email", amount=149,
                currency="INR", description="smartbudget_pro", status="created",
            )

        with self.assertRaises(pricing.PricingError):
            pricing.reconcile_order_payment("order_no_email", "paid", payment_id="pay_456")
        with db.get_conn() as conn:
            self.assertEqual(db.list_subscriptions(conn, product="smartbudget_pro"), [])


if __name__ == "__main__":
    unittest.main()
