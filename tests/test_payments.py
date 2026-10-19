"""
Razorpay Payment Links (Offer A payment collection). Mocks the actual HTTP
call to check the real request built -- auth header, paise conversion,
body shape -- not just source inspection. No live Razorpay account was
available this session; treat the first real --create-payment-link as the
verification step, same as this project's Telegram/Sheets integrations.
"""
import base64
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import payments


class TestAuthHeader(unittest.TestCase):
    def test_builds_correct_basic_auth(self):
        header = payments._auth_header("key123", "secret456")
        expected = "Basic " + base64.b64encode(b"key123:secret456").decode()
        self.assertEqual(header, expected)

    def test_missing_key_id_raises(self):
        with self.assertRaises(payments.RazorpayError):
            payments._auth_header(None, "secret456")

    def test_missing_key_secret_raises(self):
        with self.assertRaises(payments.RazorpayError):
            payments._auth_header("key123", None)


class TestCreatePaymentLink(unittest.TestCase):
    def test_converts_rupees_to_paise(self):
        captured = {}

        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            captured["body"] = body
            captured["method"] = method
            return {"id": "plink_abc", "short_url": "https://rzp.io/i/abc", "status": "created", "amount": 99900}

        with patch.object(payments, "_call", fake_call):
            result = payments.create_payment_link("key123", "secret456", 999.0, "Website Health Audit")

        self.assertEqual(captured["body"]["amount"], 99900)  # 999.0 INR -> 99900 paise
        self.assertEqual(captured["body"]["currency"], "INR")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(result["short_url"], "https://rzp.io/i/abc")
        self.assertEqual(result["amount_inr"], 999.0)

    def test_zero_amount_rejected_before_any_network_call(self):
        with patch.object(payments, "_call") as mock_call:
            with self.assertRaises(payments.RazorpayError):
                payments.create_payment_link("key123", "secret456", 0, "desc")
        mock_call.assert_not_called()

    def test_negative_amount_rejected(self):
        with self.assertRaises(payments.RazorpayError):
            payments.create_payment_link("key123", "secret456", -50, "desc")

    def test_customer_details_included_when_provided(self):
        captured = {}

        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            captured["body"] = body
            return {"id": "plink_1", "short_url": "https://rzp.io/i/1", "status": "created", "amount": 50000}

        with patch.object(payments, "_call", fake_call):
            payments.create_payment_link("key123", "secret456", 500.0, "desc",
                                          customer_name="Flour & Co.", customer_contact="9998887777")

        self.assertEqual(captured["body"]["customer"]["name"], "Flour & Co.")
        self.assertEqual(captured["body"]["customer"]["contact"], "9998887777")
        self.assertTrue(captured["body"]["notify"]["sms"])

    def test_no_customer_key_when_nothing_provided(self):
        captured = {}

        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            captured["body"] = body
            return {"id": "plink_2", "short_url": "https://rzp.io/i/2", "status": "created", "amount": 50000}

        with patch.object(payments, "_call", fake_call):
            payments.create_payment_link("key123", "secret456", 500.0, "desc")

        self.assertNotIn("customer", captured["body"])

    def test_reference_id_included_when_provided(self):
        captured = {}

        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            captured["body"] = body
            return {"id": "plink_3", "short_url": "https://rzp.io/i/3", "status": "created", "amount": 50000}

        with patch.object(payments, "_call", fake_call):
            payments.create_payment_link("key123", "secret456", 500.0, "desc", reference_id="web-audit:example.com")

        self.assertEqual(captured["body"]["reference_id"], "web-audit:example.com")


class TestGetPaymentLinkStatus(unittest.TestCase):
    def test_reports_paid_status_and_amount(self):
        def fake_call(method, url, key_id, key_secret, body=None, timeout=15):
            self.assertEqual(method, "GET")
            self.assertTrue(url.endswith("/plink_xyz"))
            return {"id": "plink_xyz", "status": "paid", "amount": 99900, "amount_paid": 99900}

        with patch.object(payments, "_call", fake_call):
            result = payments.get_payment_link_status("key123", "secret456", "plink_xyz")

        self.assertEqual(result["status"], "paid")
        self.assertEqual(result["amount_paid_inr"], 999.0)


class TestErrorHandling(unittest.TestCase):
    def test_http_error_wrapped_as_razorpay_error(self):
        import io
        import urllib.error

        def raise_http_error(*a, **kw):
            raise urllib.error.HTTPError("url", 401, "Unauthorized", {}, io.BytesIO(b'{"error": "bad auth"}'))

        with patch("urllib.request.urlopen", side_effect=raise_http_error):
            with self.assertRaises(payments.RazorpayError):
                payments.create_payment_link("bad_key", "bad_secret", 100, "desc")


if __name__ == "__main__":
    unittest.main()
