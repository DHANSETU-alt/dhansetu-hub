import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class TestPaymentRouteSecurity(unittest.TestCase):
    def test_payment_routes_never_accept_browser_credentials(self):
        files = [
            ROOT / "dashboard/app/api/blackboxops/razorpay-order/route.ts",
            ROOT / "dashboard/app/api/blackboxops/razorpay-verify/route.ts",
            ROOT / "dashboard/app/api/blackboxops/subscribe/route.ts",
            ROOT / "dashboard/app/blackboxops-os/pricing/page.tsx",
        ]
        forbidden = ("razorpaySecret", "razorpayKeyId", "payuSalt", "payuKey")
        for path in files:
            source = path.read_text()
            for name in forbidden:
                self.assertNotIn(name, source, f"{path.relative_to(ROOT)} accepts or renders {name}")

    def test_server_secrets_are_not_passed_in_process_arguments(self):
        routes = [
            ROOT / "dashboard/app/api/blackboxops/razorpay-order/route.ts",
            ROOT / "dashboard/app/api/blackboxops/razorpay-verify/route.ts",
            ROOT / "dashboard/app/api/blackboxops/subscribe/route.ts",
        ]
        forbidden_flags = ("--razorpay-key-id", "--razorpay-key-secret", "--payu-merchant-key", "--payu-merchant-salt")
        for path in routes:
            source = path.read_text()
            for flag in forbidden_flags:
                self.assertNotIn(flag, source, f"{path.relative_to(ROOT)} leaks a secret through argv")

    def test_order_route_never_accepts_client_amount_or_receipt(self):
        path = ROOT / "dashboard/app/api/blackboxops/razorpay-order/route.ts"
        source = path.read_text()
        self.assertNotIn("amountInr", source)
        self.assertNotIn("body.receipt", source)
        self.assertNotIn("{ receipt", source)
        self.assertNotIn(", receipt", source)


if __name__ == "__main__":
    unittest.main()
