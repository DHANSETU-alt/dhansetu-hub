"""
payment_gateway_manager.py. Mocks the actual HTTP calls to check the real
request shapes built (Stripe's bracket-notation form encoding, Razorpay's
JSON body) -- not live-verified against real Stripe/Razorpay accounts, no
API keys were available. UPI link generation needs no gateway account at
all, so it's tested as a real, unmocked function.
"""
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import payment_gateway_manager as pgm
from orchestrator import payments as razorpay_links


class TestUpiLinkGeneration(unittest.TestCase):
    def test_generates_valid_upi_uri(self):
        link = pgm.generate_upi_link("founder@okhdfcbank", "Shakthi Founder", 999.0, note="Website Audit")
        self.assertTrue(link.startswith("upi://pay?"))
        self.assertIn("pa=founder%40okhdfcbank", link)
        self.assertIn("am=999.00", link)
        self.assertIn("cu=INR", link)

    def test_invalid_vpa_rejected(self):
        with self.assertRaises(pgm.PaymentGatewayError):
            pgm.generate_upi_link("not-a-valid-vpa", "Name", 100.0)

    def test_zero_amount_rejected(self):
        with self.assertRaises(pgm.PaymentGatewayError):
            pgm.generate_upi_link("founder@okhdfcbank", "Name", 0)

    def test_note_omitted_when_not_given(self):
        link = pgm.generate_upi_link("founder@okhdfcbank", "Name", 100.0)
        self.assertNotIn("tn=", link)


class TestStripeCheckout(unittest.TestCase):
    def test_builds_bracket_notation_form_body(self):
        captured = {}

        def fake_stripe_call(secret_key, path, form_body):
            captured["path"] = path
            captured["body"] = form_body
            return {"id": "cs_test_123", "url": "https://checkout.stripe.com/pay/cs_test_123"}

        with patch.object(pgm, "_stripe_call", fake_stripe_call):
            result = pgm.create_stripe_checkout_session(
                "sk_test_abc", 49.99, "usd", "Website Audit", "https://x.com/ok", "https://x.com/cancel"
            )

        self.assertEqual(captured["path"], "/checkout/sessions")
        self.assertEqual(captured["body"]["line_items[0][price_data][unit_amount]"], 4999)
        self.assertEqual(captured["body"]["line_items[0][price_data][currency]"], "usd")
        self.assertEqual(result["checkout_url"], "https://checkout.stripe.com/pay/cs_test_123")

    def test_missing_secret_key_rejected(self):
        with self.assertRaises(pgm.PaymentGatewayError):
            pgm.create_stripe_checkout_session(None, 10, "usd", "desc", "https://x.com/ok", "https://x.com/cancel")

    def test_negative_amount_rejected(self):
        with self.assertRaises(pgm.PaymentGatewayError):
            pgm.create_stripe_checkout_session("sk_test", -5, "usd", "desc", "https://x.com/ok", "https://x.com/cancel")


class TestRazorpaySubscriptions(unittest.TestCase):
    def test_create_plan_converts_rupees_to_paise(self):
        captured = {}

        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            captured["body"] = body
            captured["url"] = url
            return {"id": "plan_abc"}

        with patch.object(razorpay_links, "_call", fake_call):
            result = pgm.create_razorpay_subscription_plan("key", "secret", 999.0, "Monthly Audit Plan")

        self.assertEqual(captured["body"]["item"]["amount"], 99900)
        self.assertTrue(captured["url"].endswith("/plans"))
        self.assertEqual(result["plan_id"], "plan_abc")

    def test_create_subscription(self):
        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            return {"id": "sub_xyz", "short_url": "https://rzp.io/sub/xyz", "status": "created"}

        with patch.object(razorpay_links, "_call", fake_call):
            result = pgm.create_razorpay_subscription("key", "secret", "plan_abc")

        self.assertEqual(result["subscription_id"], "sub_xyz")
        self.assertEqual(result["status"], "created")


class TestPayuHash(unittest.TestCase):
    def test_hash_matches_independently_built_reference_string(self):
        """Builds the documented pipe-delimited string by hand (not via
        pgm's own list-join) and checks the two agree -- catches a
        miscounted pipe that a self-consistency test would miss."""
        reference = "|".join([
            "testkey", "txn123", "100.00", "PDF Studio Subscription", "Soham", "test@example.com",
            "", "", "", "", "", "", "", "", "", "", "testsalt",
        ])
        expected = hashlib.sha512(reference.encode()).hexdigest()
        actual = pgm._payu_hash("testkey", "txn123", "100.00", "PDF Studio Subscription", "Soham", "test@example.com", "testsalt")
        self.assertEqual(actual, expected)

    def test_hash_changes_with_udf_fields(self):
        base = pgm._payu_hash("key", "txn", "100.00", "product", "name", "email@x.com", "salt")
        with_udf = pgm._payu_hash("key", "txn", "100.00", "product", "name", "email@x.com", "salt", udf1="ref123")
        self.assertNotEqual(base, with_udf)

    def test_different_amount_produces_different_hash(self):
        h1 = pgm._payu_hash("key", "txn", "100.00", "product", "name", "e@x.com", "salt")
        h2 = pgm._payu_hash("key", "txn", "499.00", "product", "name", "e@x.com", "salt")
        self.assertNotEqual(h1, h2)


class TestCreatePayuCheckout(unittest.TestCase):
    def test_builds_real_form_fields(self):
        result = pgm.create_payu_checkout(
            "merchantkey", "merchantsalt", 100.0, "PDF Studio — Annual",
            "test@example.com", "Soham", "9998887777",
            "https://dhansetuhub.in/pay/success", "https://dhansetuhub.in/pay/failure",
        )
        self.assertEqual(result["action_url"], pgm.PAYU_TEST_URL)
        self.assertEqual(result["fields"]["key"], "merchantkey")
        self.assertEqual(result["fields"]["amount"], "100.00")
        self.assertEqual(len(result["txnid"]), 20)
        self.assertIn("hash", result["fields"])

    def test_production_mode_uses_production_url(self):
        result = pgm.create_payu_checkout("k", "s", 100.0, "p", "e@x.com", "n", "1", "https://x.com/s", "https://x.com/f", test_mode=False)
        self.assertEqual(result["action_url"], pgm.PAYU_PRODUCTION_URL)

    def test_missing_credentials_rejected(self):
        with self.assertRaises(pgm.PaymentGatewayError):
            pgm.create_payu_checkout(None, None, 100.0, "p", "e@x.com", "n", "1", "https://x.com/s", "https://x.com/f")

    def test_negative_amount_rejected(self):
        with self.assertRaises(pgm.PaymentGatewayError):
            pgm.create_payu_checkout("k", "s", -5, "p", "e@x.com", "n", "1", "https://x.com/s", "https://x.com/f")

    def test_each_checkout_gets_a_unique_txnid(self):
        r1 = pgm.create_payu_checkout("k", "s", 100.0, "p", "e@x.com", "n", "1", "https://x.com/s", "https://x.com/f")
        r2 = pgm.create_payu_checkout("k", "s", 100.0, "p", "e@x.com", "n", "1", "https://x.com/s", "https://x.com/f")
        self.assertNotEqual(r1["txnid"], r2["txnid"])


class TestVerifyPayuResponseHash(unittest.TestCase):
    def test_correct_hash_verifies(self):
        salt, key = "mysalt", "mykey"
        fields = [salt, "success", "", "", "", "", "", "e@x.com", "Name", "product", "100.00", "txn1", key]
        real_hash = hashlib.sha512("|".join(fields).encode()).hexdigest()
        self.assertTrue(pgm.verify_payu_response_hash(key, salt, "success", "txn1", "100.00", "product", "Name", "e@x.com", real_hash))

    def test_tampered_hash_rejected(self):
        self.assertFalse(pgm.verify_payu_response_hash("key", "salt", "success", "txn1", "100.00", "product", "Name", "e@x.com", "not-a-real-hash"))

    def test_tampered_amount_rejected(self):
        salt, key = "mysalt", "mykey"
        fields = [salt, "success", "", "", "", "", "", "e@x.com", "Name", "product", "100.00", "txn1", key]
        real_hash = hashlib.sha512("|".join(fields).encode()).hexdigest()
        # attacker changes the amount but replays the original hash
        self.assertFalse(pgm.verify_payu_response_hash(key, salt, "success", "txn1", "999.00", "product", "Name", "e@x.com", real_hash))


class TestGatewayStatus(unittest.TestCase):
    def test_unconfigured_gateways_report_false(self):
        status = pgm.gateway_status()
        self.assertFalse(status["razorpay"]["configured"])
        self.assertFalse(status["stripe"]["configured"])
        self.assertFalse(status["upi"]["configured"])
        self.assertFalse(status["payu"]["configured"])

    def test_payu_configured_when_both_key_and_salt_given(self):
        status = pgm.gateway_status(payu_merchant_key="k", payu_merchant_salt="s")
        self.assertTrue(status["payu"]["configured"])
        self.assertIsNone(status["payu"]["valid"])  # no cheap ping endpoint exists

    def test_never_returns_actual_credentials(self):
        status = pgm.gateway_status(razorpay_key_id="secret_key_123", stripe_secret_key="sk_live_secret456",
                                     payu_merchant_key="payukey789", payu_merchant_salt="payusaltXYZ")
        dumped = str(status)
        self.assertNotIn("secret_key_123", dumped)
        self.assertNotIn("sk_live_secret456", dumped)
        self.assertNotIn("payukey789", dumped)
        self.assertNotIn("payusaltXYZ", dumped)

    def test_valid_upi_vpa_reports_valid(self):
        status = pgm.gateway_status(upi_vpa="founder@okhdfcbank")
        self.assertTrue(status["upi"]["configured"])
        self.assertTrue(status["upi"]["valid"])

    def test_invalid_upi_vpa_reports_invalid(self):
        status = pgm.gateway_status(upi_vpa="not-a-vpa")
        self.assertFalse(status["upi"]["valid"])


if __name__ == "__main__":
    unittest.main()
