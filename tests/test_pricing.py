import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import cli, db, pricing


class PricingTestBase(unittest.TestCase):
    def setUp(self):
        self._orig_db_path = db.config.DB_PATH
        self._tmp_dir = tempfile.mkdtemp(prefix="shakthi_pricing_test_")
        db.config.DB_PATH = f"{self._tmp_dir}/test.db"
        db.init_db()

    def tearDown(self):
        import shutil
        db.config.DB_PATH = self._orig_db_path
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


class TestCheckAccess(PricingTestBase):
    def test_new_email_gets_full_free_tier(self):
        result = pricing.check_access("new@example.com", "pdf_studio")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["remaining_free"], 10)

    def test_usage_decrements_remaining_free(self):
        for _ in range(3):
            pricing.record_usage("user@example.com", "pdf_studio")
        result = pricing.check_access("user@example.com", "pdf_studio")
        self.assertEqual(result["remaining_free"], 7)

    def test_exhausted_free_tier_requires_payment(self):
        for _ in range(10):
            pricing.record_usage("heavy@example.com", "pdf_studio")
        result = pricing.check_access("heavy@example.com", "pdf_studio")
        self.assertFalse(result["allowed"])
        self.assertTrue(result["requires_payment"])
        self.assertEqual(result["price_inr"], 99)

    def test_peopledesk_has_zero_free_uses(self):
        result = pricing.check_access("anyone@example.com", "peopledesk")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["price_inr"], 99)

    def test_unknown_product_rejected(self):
        with self.assertRaises(pricing.PricingError):
            pricing.check_access("e@x.com", "not_a_real_product")

    def test_active_subscription_grants_access_even_after_exhausting_free_tier(self):
        for _ in range(10):
            pricing.record_usage("subscriber@example.com", "pdf_studio")
        with db.get_conn() as conn:
            sub_id = db.insert_subscription(conn, "subscriber@example.com", "pdf_studio", 100, "razorpay", gateway_ref="plink_1")
        confirmed = pricing.confirm_subscription_paid(sub_id)
        self.assertEqual(confirmed["status"], "active")

        result = pricing.check_access("subscriber@example.com", "pdf_studio")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "active subscription")

    def test_expired_subscription_does_not_grant_access(self):
        with db.get_conn() as conn:
            sub_id = db.insert_subscription(conn, "expired@example.com", "pdf_studio", 100, "razorpay", gateway_ref="plink_2")
            db.activate_subscription(conn, sub_id, "2020-01-01 00:00:00")  # already expired
        for _ in range(10):
            pricing.record_usage("expired@example.com", "pdf_studio")
        result = pricing.check_access("expired@example.com", "pdf_studio")
        self.assertFalse(result["allowed"])

    def test_different_emails_have_independent_free_tiers(self):
        for _ in range(10):
            pricing.record_usage("a@example.com", "pdf_studio")
        result_a = pricing.check_access("a@example.com", "pdf_studio")
        result_b = pricing.check_access("b@example.com", "pdf_studio")
        self.assertFalse(result_a["allowed"])
        self.assertTrue(result_b["allowed"])


class TestCreateSubscriptionPayment(PricingTestBase):
    def test_razorpay_path_calls_real_link_creation(self):
        fake_link = {"id": "plink_abc", "short_url": "https://rzp.io/i/abc", "status": "created", "amount_inr": 100.0}
        with patch("orchestrator.payment_gateway_manager.create_razorpay_payment_link", return_value=fake_link):
            result = pricing.create_subscription_payment(
                "e@x.com", "pdf_studio", "razorpay", razorpay_key_id="k", razorpay_key_secret="s")
        self.assertEqual(result["gateway"], "razorpay")
        self.assertEqual(result["checkout"], "https://rzp.io/i/abc")

    def test_payu_path_calls_real_checkout_creation(self):
        fake_checkout = {"action_url": "https://test.payu.in/_payment", "txnid": "txn123", "fields": {"hash": "x"}}
        with patch("orchestrator.payment_gateway_manager.create_payu_checkout", return_value=fake_checkout):
            result = pricing.create_subscription_payment(
                "e@x.com", "pdf_studio", "payu", payu_merchant_key="k", payu_merchant_salt="s",
                success_url="https://x.com/ok", failure_url="https://x.com/fail")
        self.assertEqual(result["gateway"], "payu")
        self.assertEqual(result["gateway_ref"], "txn123")

    def test_unknown_gateway_rejected(self):
        with self.assertRaises(pricing.PricingError):
            pricing.create_subscription_payment("e@x.com", "pdf_studio", "paypal")


class TestOneTimeCappedProducts(PricingTestBase):
    """Real tests for the 300-founding-customer cap (founder instruction,
    2026-09-09): blackboxops_os_starter/growth are one-time purchases
    (is_one_time=True, period_days=None) with a hard max_customers limit,
    enforced by counting only genuinely 'active'/'paid' rows -- a pending/
    abandoned checkout must never occupy a slot."""

    def test_product_is_marked_one_time_with_no_expiry_period(self):
        cfg = pricing.PRODUCT_PRICING["blackboxops_os_starter"]
        self.assertTrue(cfg["is_one_time"])
        self.assertIsNone(cfg["period_days"])
        self.assertEqual(cfg["max_customers"], 300)

    def test_confirm_paid_sets_no_expiry_for_one_time_product(self):
        """Regression test, 2026-09-10: confirm_subscription_paid() used to
        set a 365-day valid_until unconditionally, so a founding customer's
        "one-time, lifetime" ₹2999 purchase would have silently expired in
        a year. It must set valid_until=NULL instead, and access must still
        be granted long after what would have been the old expiry date."""
        with db.get_conn() as conn:
            sub_id = db.insert_subscription(conn, "lifetime@example.com", "blackboxops_os_starter", 2999, "razorpay", gateway_ref="order_1")
        confirmed = pricing.confirm_subscription_paid(sub_id)
        self.assertIsNone(confirmed["valid_until"])

        with db.get_conn() as conn:
            row = db.get_subscription(conn, sub_id)
        self.assertIsNone(row["valid_until"])

        result = pricing.check_access("lifetime@example.com", "blackboxops_os_starter")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "active subscription")

    def test_confirm_paid_still_sets_365_day_expiry_for_recurring_product(self):
        """Same fix must not regress the existing non-one-time behavior --
        pdf_studio still gets a real 365-day valid_until, not NULL."""
        with db.get_conn() as conn:
            sub_id = db.insert_subscription(conn, "recurring@example.com", "pdf_studio", 99, "razorpay", gateway_ref="plink_9")
        confirmed = pricing.confirm_subscription_paid(sub_id)
        self.assertIsNotNone(confirmed["valid_until"])

    def test_payment_link_flow_blocked_once_cap_reached(self):
        with db.get_conn() as conn:
            for i in range(300):
                sub_id = db.insert_subscription(conn, f"c{i}@x.com", "blackboxops_os_starter", 2999, "razorpay",
                                                 gateway_ref=f"ref{i}")
                db.activate_subscription(conn, sub_id, None)  # None = lifetime, never expires

        with self.assertRaises(pricing.PricingError):
            pricing.create_subscription_payment(
                "customer_301@x.com", "blackboxops_os_starter", "razorpay",
                razorpay_key_id="k", razorpay_key_secret="s")

    def test_payment_link_flow_allowed_under_cap(self):
        fake_link = {"id": "plink_x", "short_url": "https://rzp.io/i/x", "status": "created", "amount_inr": 2999}
        with db.get_conn() as conn:
            for i in range(299):
                sub_id = db.insert_subscription(conn, f"c{i}@x.com", "blackboxops_os_starter", 2999, "razorpay",
                                                 gateway_ref=f"ref{i}")
                db.activate_subscription(conn, sub_id, None)

        with patch("orchestrator.payment_gateway_manager.create_razorpay_payment_link", return_value=fake_link):
            result = pricing.create_subscription_payment(
                "customer_300@x.com", "blackboxops_os_starter", "razorpay",
                razorpay_key_id="k", razorpay_key_secret="s")
        self.assertEqual(result["gateway"], "razorpay")

    def test_pending_subscriptions_do_not_count_toward_cap(self):
        with db.get_conn() as conn:
            # 300 PENDING (never activated) rows -- none of these are real
            # paid customers, so none should occupy a slot.
            for i in range(300):
                db.insert_subscription(conn, f"c{i}@x.com", "blackboxops_os_starter", 2999, "razorpay",
                                        gateway_ref=f"ref{i}")

        fake_link = {"id": "plink_y", "short_url": "https://rzp.io/i/y", "status": "created", "amount_inr": 2999}
        with patch("orchestrator.payment_gateway_manager.create_razorpay_payment_link", return_value=fake_link):
            result = pricing.create_subscription_payment(
                "real_customer@x.com", "blackboxops_os_starter", "razorpay",
                razorpay_key_id="k", razorpay_key_secret="s")
        self.assertEqual(result["gateway"], "razorpay")

    def test_uncapped_product_never_checks_the_limit(self):
        fake_link = {"id": "plink_z", "short_url": "https://rzp.io/i/z", "status": "created", "amount_inr": 99}
        # pdf_studio has no max_customers -- must not raise regardless of
        # how many subscriptions already exist for it.
        with db.get_conn() as conn:
            for i in range(500):
                sub_id = db.insert_subscription(conn, f"c{i}@x.com", "pdf_studio", 99, "razorpay", gateway_ref=f"r{i}")
                db.activate_subscription(conn, sub_id, "2099-01-01 00:00:00")

        with patch("orchestrator.payment_gateway_manager.create_razorpay_payment_link", return_value=fake_link):
            result = pricing.create_subscription_payment(
                "another@x.com", "pdf_studio", "razorpay", razorpay_key_id="k", razorpay_key_secret="s")
        self.assertEqual(result["gateway"], "razorpay")


class TestCountPaidTransactionsForProduct(PricingTestBase):
    """The Razorpay Orders/Checkout.js flow (the actual live checkout on
    the pricing page) writes to payment_transactions, a DIFFERENT table
    than the Payment-Links flow above -- this is the cap-count function
    that flow actually uses (see cli.py's _cmd_create_razorpay_order)."""

    def test_counts_only_paid_status_for_the_exact_product(self):
        with db.get_conn() as conn:
            db.insert_payment_transaction(conn, gateway="razorpay_order", gateway_ref="o1", amount=2999,
                                           currency="INR", description="blackboxops_os_starter", status="paid")
            db.insert_payment_transaction(conn, gateway="razorpay_order", gateway_ref="o2", amount=2999,
                                           currency="INR", description="blackboxops_os_starter", status="created")
            db.insert_payment_transaction(conn, gateway="razorpay_order", gateway_ref="o3", amount=7999,
                                           currency="INR", description="blackboxops_os_growth", status="paid")
            count = db.count_paid_transactions_for_product(conn, "blackboxops_os_starter")
        self.assertEqual(count, 1)


class TestDhanSetuProductCatalog(unittest.TestCase):
    def test_one_time_prices_are_server_authoritative(self):
        self.assertEqual(pricing.PRODUCT_PRICING["smartbudget_pro"]["price_inr"], 149)
        self.assertEqual(pricing.PRODUCT_PRICING["dhansetu_all_access"]["price_inr"], 399)
        self.assertTrue(pricing.PRODUCT_PRICING["smartbudget_pro"]["is_one_time"])
        self.assertTrue(pricing.PRODUCT_PRICING["dhansetu_all_access"]["is_one_time"])

    def test_order_product_rejects_unknown_product(self):
        with self.assertRaises(pricing.PricingError):
            pricing.resolve_order_product("client_invented_product")

    def test_order_product_returns_catalog_amount_not_client_amount(self):
        product = pricing.resolve_order_product("smartbudget_pro")
        self.assertEqual(product["price_inr"], 149)
        self.assertEqual(product["amount_paise"], 14900)


class TestServerAuthoritativeOrder(PricingTestBase):
    def test_client_amount_is_ignored_for_known_product(self):
        created = {}

        def fake_create(key_id, key_secret, amount_inr, receipt):
            created.update(amount_inr=amount_inr, receipt=receipt)
            return {"order_id": "order_server_price", "amount": 14900, "currency": "INR"}

        with patch("orchestrator.payment_gateway_manager.create_razorpay_order", side_effect=fake_create):
            with redirect_stdout(StringIO()):
                cli._cmd_create_razorpay_order(
                    "key", "secret", 1, "server-generated-reference", "ignored", "smartbudget_pro"
                )

        self.assertEqual(created["amount_inr"], 149)
        with db.get_conn() as conn:
            transaction = db.get_payment_transaction(conn, "order_server_price")
        self.assertEqual(transaction["amount"], 149)
        self.assertEqual(transaction["description"], "smartbudget_pro")


if __name__ == "__main__":
    unittest.main()
