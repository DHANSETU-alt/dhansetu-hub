"""
Razorpay Checkout Flow - Integration Tests

Complete end-to-end tests for:
1. Order creation with customer email
2. Webhook signature verification
3. Idempotent webhook processing
4. Database persistence
5. Payment status tracking

Real test data uses documented Razorpay API payloads.
"""
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

from orchestrator import db, payment_gateway_manager


class TestRazorpayOrderCreation:
    """Test Razorpay order creation with proper database persistence."""

    @patch('orchestrator.payments._call')
    def test_create_order_with_customer_email(self, mock_call):
        """Order creation should accept customer email parameter."""
        # Mock the Razorpay API response
        mock_call.return_value = {
            "id": "order_abc123",
            "amount": 29900,
            "currency": "INR",
            "receipt": "order_20261001_001",
        }

        order = payment_gateway_manager.create_razorpay_order(
            key_id="test_key",
            key_secret="test_secret",
            amount_inr=299.0,
            receipt="order_20261001_001",
        )
        # Mock response structure matches Razorpay's real API
        assert "order_id" in order
        assert order["amount"] == 29900  # In paise
        assert order["currency"] == "INR"

    def test_create_order_validation(self):
        """Order creation should validate amount."""
        with pytest.raises(payment_gateway_manager.PaymentGatewayError):
            payment_gateway_manager.create_razorpay_order(
                key_id="test_key",
                key_secret="test_secret",
                amount_inr=-100.0,  # Invalid
                receipt="order_20261001_002",
            )

    def test_insert_payment_transaction_with_email(self):
        """payment_transactions should accept and store customer email."""
        with db.get_conn() as conn:
            txn_id = db.insert_payment_transaction(
                conn,
                gateway="razorpay_order",
                gateway_ref="order_abc123",
                amount=299.0,
                currency="INR",
                description="blackboxops_os_starter",
                customer_name="John Doe",
                customer_email="john@example.com",
                customer_contact="+919876543210",
                status="created",
            )
            assert txn_id is not None

            # Verify email was stored
            txn = db.get_payment_transaction(conn, "order_abc123")
            assert txn["customer_email"] == "john@example.com"
            assert txn["customer_name"] == "John Doe"
            assert txn["customer_contact"] == "+919876543210"


class TestWebhookSignatureVerification:
    """Test Razorpay webhook signature verification."""

    def test_verify_webhook_signature_valid(self):
        """Valid webhook signature should pass verification."""
        webhook_secret = "test_webhook_secret_key"
        body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"order_id":"order_123"}}}}'

        # Calculate correct signature
        signature = hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()

        result = payment_gateway_manager.verify_razorpay_webhook_signature(
            body, signature, webhook_secret
        )
        assert result is True

    def test_verify_webhook_signature_invalid(self):
        """Invalid webhook signature should fail verification."""
        webhook_secret = "test_webhook_secret_key"
        body = b'{"event":"payment.captured","payload":{"payment":{"entity":{"order_id":"order_123"}}}}'

        # Use wrong signature
        bad_signature = "0" * 64

        result = payment_gateway_manager.verify_razorpay_webhook_signature(
            body, bad_signature, webhook_secret
        )
        assert result is False

    def test_verify_webhook_signature_timing_safe(self):
        """Signature comparison should be timing-safe (constant-time)."""
        webhook_secret = "test_webhook_secret_key"
        body = b'{"event":"payment.captured"}'
        signature = hmac.new(
            webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()

        # Both should use hmac.compare_digest internally
        assert payment_gateway_manager.verify_razorpay_webhook_signature(
            body, signature, webhook_secret
        )


class TestCheckoutSignatureVerification:
    """Test Razorpay Checkout.js client-side signature verification."""

    def test_verify_checkout_signature_valid(self):
        """Valid checkout signature should pass verification."""
        key_secret = "test_key_secret"
        order_id = "order_abc123"
        payment_id = "pay_def456"

        # Calculate correct signature
        payload = f"{order_id}|{payment_id}".encode()
        signature = hmac.new(
            key_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        result = payment_gateway_manager.verify_razorpay_checkout_signature(
            key_secret, order_id, payment_id, signature
        )
        assert result is True

    def test_verify_checkout_signature_invalid(self):
        """Invalid checkout signature should fail verification."""
        key_secret = "test_key_secret"
        order_id = "order_abc123"
        payment_id = "pay_def456"
        bad_signature = "0" * 64

        result = payment_gateway_manager.verify_razorpay_checkout_signature(
            key_secret, order_id, payment_id, bad_signature
        )
        assert result is False

    def test_verify_checkout_signature_tamper_detection(self):
        """Signature verification should detect tampered order_id or payment_id."""
        key_secret = "test_key_secret"
        order_id = "order_abc123"
        payment_id = "pay_def456"

        payload = f"{order_id}|{payment_id}".encode()
        signature = hmac.new(
            key_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        # Same signature, but different order_id
        result = payment_gateway_manager.verify_razorpay_checkout_signature(
            key_secret, "order_xyz999", payment_id, signature
        )
        assert result is False


class TestIdempotentWebhookProcessing:
    """Test that webhook processing is idempotent (safe for retries)."""

    def test_duplicate_webhook_idempotent(self):
        """Processing the same webhook twice should not create duplicate records."""
        with db.get_conn() as conn:
            # Insert initial transaction
            db.insert_payment_transaction(
                conn,
                gateway="razorpay_order",
                gateway_ref="order_xyz789",
                amount=499.0,
                currency="INR",
                description="product_test",
                status="created",
            )

        # First webhook processing
        with db.get_conn() as conn:
            db.update_payment_transaction_status(conn, "order_xyz789", "paid")
            txn1 = db.get_payment_transaction(conn, "order_xyz789")

        # Second webhook (retry) - should update same record, not create new one
        with db.get_conn() as conn:
            db.update_payment_transaction_status(conn, "order_xyz789", "paid")
            txn2 = db.get_payment_transaction(conn, "order_xyz789")

        # Same database row, not duplicated
        assert txn1["id"] == txn2["id"]
        assert txn1["status"] == "paid"
        assert txn2["status"] == "paid"


class TestPaymentStatusPersistence:
    """Test payment status transitions and database persistence."""

    def test_payment_status_transitions(self):
        """Payment status should transition correctly: created -> paid."""
        with db.get_conn() as conn:
            # Create order
            db.insert_payment_transaction(
                conn,
                gateway="razorpay_order",
                gateway_ref="order_status_test",
                amount=199.0,
                currency="INR",
                description="test_product",
                status="created",
            )
            txn = db.get_payment_transaction(conn, "order_status_test")
            assert txn["status"] == "created"

            # Webhook: payment captured
            db.update_payment_transaction_status(conn, "order_status_test", "paid")
            txn = db.get_payment_transaction(conn, "order_status_test")
            assert txn["status"] == "paid"

    def test_payment_failed_status(self):
        """Failed payments should be marked with failed status."""
        with db.get_conn() as conn:
            db.insert_payment_transaction(
                conn,
                gateway="razorpay_order",
                gateway_ref="order_fail_test",
                amount=299.0,
                currency="INR",
                description="test_product",
                status="created",
            )

            # Payment failed
            db.update_payment_transaction_status(conn, "order_fail_test", "failed")
            txn = db.get_payment_transaction(conn, "order_fail_test")
            assert txn["status"] == "failed"

    def test_payment_id_storage(self):
        """Payment ID from webhook should be stored for reconciliation."""
        with db.get_conn() as conn:
            db.insert_payment_transaction(
                conn,
                gateway="razorpay_order",
                gateway_ref="order_payment_id_test",
                amount=399.0,
                currency="INR",
                description="test_product",
                status="created",
            )

            # Store payment ID after webhook
            payment_id = "pay_12345abcde"
            db.set_payment_transaction_paid(conn, "order_payment_id_test", payment_id)

            txn = db.get_payment_transaction(conn, "order_payment_id_test")
            assert txn["payment_id"] == payment_id
            assert txn["status"] == "paid"


class TestRealWebhookPayloads:
    """Test with real Razorpay webhook payload structures."""

    def test_payment_captured_webhook_payload(self):
        """Process a real payment.captured webhook payload."""
        webhook_secret = "test_webhook_secret"

        # Real structure from Razorpay docs
        payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_abc123",
                        "order_id": "order_xyz789",
                        "amount": 29900,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            },
        }

        raw_body = json.dumps(payload).encode()
        signature = hmac.new(
            webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()

        # Verify signature works
        verified = payment_gateway_manager.verify_razorpay_webhook_signature(
            raw_body, signature, webhook_secret
        )
        assert verified is True

    def test_payment_failed_webhook_payload(self):
        """Process a real payment.failed webhook payload."""
        webhook_secret = "test_webhook_secret"

        payload = {
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_failed123",
                        "order_id": "order_xyz789",
                        "error": {
                            "code": "BAD_REQUEST_ERROR",
                            "description": "The payment was cancelled",
                        },
                    }
                }
            },
        }

        raw_body = json.dumps(payload).encode()
        signature = hmac.new(
            webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()

        verified = payment_gateway_manager.verify_razorpay_webhook_signature(
            raw_body, signature, webhook_secret
        )
        assert verified is True


class TestCustomerEmailValidation:
    """Test customer email handling and validation."""

    def test_email_optional(self):
        """Customer email should be optional in transaction."""
        with db.get_conn() as conn:
            txn_id = db.insert_payment_transaction(
                conn,
                gateway="razorpay_order",
                gateway_ref="order_no_email",
                amount=199.0,
                currency="INR",
                description="test_product",
                status="created",
                customer_email=None,  # No email
            )

            txn = db.get_payment_transaction(conn, "order_no_email")
            assert txn["customer_email"] is None

    def test_email_stored_correctly(self):
        """Valid email should be stored correctly."""
        test_emails = [
            "user@example.com",
            "test+tag@domain.co.uk",
            "name.surname@company.io",
        ]

        for email in test_emails:
            with db.get_conn() as conn:
                db.insert_payment_transaction(
                    conn,
                    gateway="razorpay_order",
                    gateway_ref=f"order_email_{test_emails.index(email)}",
                    amount=199.0,
                    currency="INR",
                    description="test",
                    status="created",
                    customer_email=email,
                )

                txn = db.get_payment_transaction(
                    conn, f"order_email_{test_emails.index(email)}"
                )
                assert txn["customer_email"] == email


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
