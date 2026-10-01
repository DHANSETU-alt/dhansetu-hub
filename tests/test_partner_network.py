"""
Partner Network System Tests -- onboarding, commissions, payouts, referrals.

Coverage:
  - Partner signup and approval workflow
  - Commission calculation accuracy
  - Referral tracking (clicks, conversions)
  - Payout processing (net-30 terms)
  - Partner stats/analytics
  - Permission checks (partner-only dashboard)
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal

# Import the partner network model
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'orchestrator'))

from partner_network_model import (
    PartnerTier,
    PartnerStatus,
    CommissionStatus,
    PayoutStatus,
    create_partner,
    get_partner,
    get_partner_by_email,
    approve_partner,
    activate_partner,
    record_commission,
    get_commissions,
    get_partner_stats,
    request_payout,
    process_payout,
    get_payouts,
    track_click,
)
from db import get_conn, init_db


@pytest.fixture
def clean_db():
    """Initialize clean database for each test."""
    init_db()
    yield
    # Cleanup after test


class TestPartnerOnboarding:
    """Partner signup and approval workflow."""

    def test_create_affiliate_partner(self, clean_db):
        """Create affiliate partner application (pending status)."""
        result = create_partner(
            business_id=1,
            name="John Reseller",
            email="john@example.com",
            phone="+91 98765 43210",
            company="Reseller Corp",
            website="https://reseller.com",
            tier='affiliate',
        )

        assert result['id'] > 0
        assert result['name'] == "John Reseller"
        assert result['email'] == "john@example.com"
        assert result['tier'] == 'affiliate'
        assert result['commission_rate'] == 0.15
        assert result['status'] == PartnerStatus.PENDING
        assert result['referral_link'].startswith('https://app.example.com?partner_id=')

    def test_create_reseller_partner(self, clean_db):
        """Create reseller partner with 20% commission rate."""
        result = create_partner(
            business_id=1,
            name="Reseller Pro",
            email="reseller@example.com",
            tier='reseller',
        )

        assert result['commission_rate'] == 0.20
        assert result['tier'] == 'reseller'

    def test_create_agency_partner(self, clean_db):
        """Create agency partner with 25% commission rate."""
        result = create_partner(
            business_id=1,
            name="Agency Team",
            email="agency@example.com",
            tier='agency',
        )

        assert result['commission_rate'] == 0.25
        assert result['tier'] == 'agency'

    def test_duplicate_email_rejected(self, clean_db):
        """Reject duplicate email addresses."""
        create_partner(
            business_id=1,
            name="Partner 1",
            email="duplicate@example.com",
            tier='affiliate',
        )

        with pytest.raises(ValueError, match="already registered"):
            create_partner(
                business_id=1,
                name="Partner 2",
                email="duplicate@example.com",
                tier='affiliate',
            )

    def test_invalid_tier_rejected(self, clean_db):
        """Reject invalid tier values."""
        with pytest.raises(ValueError, match="Invalid tier"):
            create_partner(
                business_id=1,
                name="Partner",
                email="partner@example.com",
                tier='invalid_tier',
            )

    def test_approve_partner(self, clean_db):
        """Founder approves pending partner application."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )
        assert partner['status'] == PartnerStatus.PENDING

        approve_partner(partner['id'], approved_by='founder@example.com')

        approved = get_partner(partner['id'])
        assert approved['status'] == PartnerStatus.APPROVED
        assert approved['approved_by'] == 'founder@example.com'
        assert approved['approved_at'] is not None

    def test_activate_partner(self, clean_db):
        """Activate approved partner (approved -> active)."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )
        approve_partner(partner['id'], 'founder@example.com')

        activate_partner(partner['id'])

        active = get_partner(partner['id'])
        assert active['status'] == PartnerStatus.ACTIVE

    def test_get_partner_by_email(self, clean_db):
        """Fetch partner by email address."""
        create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        partner = get_partner_by_email('partner@example.com')
        assert partner is not None
        assert partner['name'] == "Partner"
        assert partner['email'] == "partner@example.com"

    def test_partner_not_found(self, clean_db):
        """Return None for nonexistent partner."""
        partner = get_partner(999)
        assert partner is None


class TestCommissionCalculation:
    """Commission tracking and accuracy."""

    def test_record_affiliate_commission(self, clean_db):
        """Record commission for affiliate (15% of sale)."""
        partner = create_partner(
            business_id=1,
            name="Affiliate",
            email="affiliate@example.com",
            tier='affiliate',
        )
        activate_partner(partner['id'])

        commission = record_commission(
            partner_id=partner['id'],
            transaction_id='txn_123',
            customer_email='customer@example.com',
            amount=1000.0,
            product='Premium Plan',
        )

        assert commission['amount'] == 1000.0
        assert commission['commission_rate'] == 0.15
        assert commission['commission_amount'] == 150.0
        assert commission['status'] == CommissionStatus.EARNED

    def test_record_reseller_commission(self, clean_db):
        """Record commission for reseller (20% of sale)."""
        partner = create_partner(
            business_id=1,
            name="Reseller",
            email="reseller@example.com",
            tier='reseller',
        )
        activate_partner(partner['id'])

        commission = record_commission(
            partner_id=partner['id'],
            transaction_id='txn_456',
            customer_email='customer@example.com',
            amount=5000.0,
            product='Enterprise Plan',
        )

        assert commission['commission_amount'] == 1000.0  # 5000 * 0.20

    def test_record_agency_commission(self, clean_db):
        """Record commission for agency (25% of sale)."""
        partner = create_partner(
            business_id=1,
            name="Agency",
            email="agency@example.com",
            tier='agency',
        )
        activate_partner(partner['id'])

        commission = record_commission(
            partner_id=partner['id'],
            transaction_id='txn_789',
            customer_email='customer@example.com',
            amount=10000.0,
            product='Custom Solution',
        )

        assert commission['commission_amount'] == 2500.0  # 10000 * 0.25

    def test_commission_history_pagination(self, clean_db):
        """Retrieve commission history with pagination."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # Record 5 commissions
        for i in range(5):
            record_commission(
                partner_id=partner['id'],
                transaction_id=f'txn_{i}',
                customer_email=f'customer{i}@example.com',
                amount=1000.0,
                product='Plan',
            )

        # Get first 3
        commissions = get_commissions(partner['id'], limit=3)
        assert len(commissions) == 3

        # Get next 2
        commissions = get_commissions(partner['id'], limit=3, offset=3)
        assert len(commissions) == 2

    def test_get_commissions_by_status(self, clean_db):
        """Filter commissions by status (earned/paid/disputed)."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # Record earned commissions
        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=1000.0,
        )
        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_2',
            customer_email='customer@example.com',
            amount=1000.0,
        )

        earned = get_commissions(partner['id'], status=CommissionStatus.EARNED)
        assert len(earned) == 2
        assert all(c['status'] == CommissionStatus.EARNED for c in earned)


class TestPartnerStats:
    """Partner performance tracking (clicks, conversions, revenue)."""

    def test_get_partner_stats(self, clean_db):
        """Retrieve partner performance stats."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # Record some activity
        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=1000.0,
        )
        track_click(partner['id'], session_id='session_1')
        track_click(partner['id'], session_id='session_2')

        stats = get_partner_stats(partner['id'])
        assert stats is not None
        assert stats['total_clicks'] == 2
        assert stats['total_conversions'] == 1
        assert stats['total_revenue'] == 1000.0
        assert stats['total_earned_commission'] == 150.0
        assert stats['conversion_rate'] == 50.0  # 1 conversion / 2 clicks

    def test_track_referral_click(self, clean_db):
        """Track referral link clicks."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        click_id_1 = track_click(partner['id'], session_id='sess_1')
        click_id_2 = track_click(partner['id'], session_id='sess_2')

        assert click_id_1 > 0
        assert click_id_2 > click_id_1

        stats = get_partner_stats(partner['id'])
        assert stats['total_clicks'] == 2

    def test_conversion_rate_calculation(self, clean_db):
        """Calculate conversion rate from clicks to sales."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # 10 clicks, 2 conversions = 20% conversion rate
        for i in range(10):
            track_click(partner['id'])

        for i in range(2):
            record_commission(
                partner_id=partner['id'],
                transaction_id=f'txn_{i}',
                customer_email=f'customer{i}@example.com',
                amount=1000.0,
            )

        stats = get_partner_stats(partner['id'])
        assert stats['total_clicks'] == 10
        assert stats['total_conversions'] == 2
        assert stats['conversion_rate'] == 20.0


class TestPayoutProcessing:
    """Payout requests and monthly payment processing."""

    def test_request_payout_minimum_amount(self, clean_db):
        """Payout request requires minimum ₹100 earned."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # Record small commission (₹50)
        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=500.0,  # 500 * 0.15 = 75
        )

        with pytest.raises(ValueError, match="Minimum payout amount"):
            request_payout(
                partner_id=partner['id'],
                payout_method='bank_transfer',
                bank_details={'account_number': '123', 'ifsc': 'BANK0001', 'beneficiary_name': 'Partner'},
            )

    def test_request_bank_payout(self, clean_db):
        """Request payout via bank transfer."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # Record ₹1500 commission (>= ₹100)
        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=10000.0,  # 10000 * 0.15 = 1500
        )

        payout = request_payout(
            partner_id=partner['id'],
            payout_method='bank_transfer',
            bank_details={
                'account_number': '1234567890',
                'ifsc': 'HDFC0001234',
                'beneficiary_name': 'Partner Name',
            },
        )

        assert payout['id'] > 0
        assert payout['total_amount'] == 1500.0
        assert payout['payout_method'] == 'bank_transfer'
        assert payout['status'] == PayoutStatus.PENDING

    def test_request_upi_payout(self, clean_db):
        """Request payout via UPI."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=10000.0,
        )

        payout = request_payout(
            partner_id=partner['id'],
            payout_method='upi',
            upi_id='partner@bank',
        )

        assert payout['payout_method'] == 'upi'
        assert payout['status'] == PayoutStatus.PENDING

    def test_request_paypal_payout(self, clean_db):
        """Request payout via PayPal."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=10000.0,
        )

        payout = request_payout(
            partner_id=partner['id'],
            payout_method='paypal',
            paypal_email='partner@paypal.com',
        )

        assert payout['payout_method'] == 'paypal'

    def test_duplicate_payout_request_rejected(self, clean_db):
        """Reject payout request if one already pending."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=10000.0,
        )

        # First request succeeds
        request_payout(
            partner_id=partner['id'],
            payout_method='bank_transfer',
            bank_details={'account_number': '123', 'ifsc': 'BANK0001', 'beneficiary_name': 'Partner'},
        )

        # Second request fails
        with pytest.raises(ValueError, match="already pending"):
            request_payout(
                partner_id=partner['id'],
                payout_method='bank_transfer',
                bank_details={'account_number': '123', 'ifsc': 'BANK0001', 'beneficiary_name': 'Partner'},
            )

    def test_process_payout(self, clean_db):
        """Process payout and mark commissions as paid."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        record_commission(
            partner_id=partner['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=10000.0,
        )

        payout = request_payout(
            partner_id=partner['id'],
            payout_method='bank_transfer',
            bank_details={'account_number': '123', 'ifsc': 'BANK0001', 'beneficiary_name': 'Partner'},
        )

        # Process payout
        process_payout(payout['id'], reference_id='transfer_receipt_123')

        # Verify payout status
        payouts = get_payouts(partner['id'])
        assert payouts[0]['status'] == PayoutStatus.PROCESSED
        assert payouts[0]['reference_id'] == 'transfer_receipt_123'

    def test_payout_history(self, clean_db):
        """Retrieve partner payout history."""
        partner = create_partner(
            business_id=1,
            name="Partner",
            email="partner@example.com",
            tier='affiliate',
        )

        # Record two commissions
        for i in range(2):
            record_commission(
                partner_id=partner['id'],
                transaction_id=f'txn_{i}',
                customer_email=f'customer{i}@example.com',
                amount=10000.0,
            )

        # Request two payouts
        payout1 = request_payout(
            partner_id=partner['id'],
            payout_method='bank_transfer',
            bank_details={'account_number': '123', 'ifsc': 'BANK0001', 'beneficiary_name': 'Partner'},
        )

        # Process first payout (clears earnings)
        process_payout(payout1['id'], 'ref_1')

        # Request second payout
        payout2 = request_payout(
            partner_id=partner['id'],
            payout_method='upi',
            upi_id='partner@bank',
        )

        payouts = get_payouts(partner['id'])
        assert len(payouts) == 2


class TestPermissions:
    """Permission checks and data isolation."""

    def test_partner_can_only_view_own_data(self, clean_db):
        """Partner can only access their own commissions/stats."""
        partner1 = create_partner(
            business_id=1,
            name="Partner 1",
            email="partner1@example.com",
            tier='affiliate',
        )
        partner2 = create_partner(
            business_id=1,
            name="Partner 2",
            email="partner2@example.com",
            tier='affiliate',
        )

        # Record commissions for partner1
        record_commission(
            partner_id=partner1['id'],
            transaction_id='txn_1',
            customer_email='customer@example.com',
            amount=1000.0,
        )

        # Verify partner1 commissions
        p1_commissions = get_commissions(partner1['id'])
        assert len(p1_commissions) == 1

        # Verify partner2 has no commissions
        p2_commissions = get_commissions(partner2['id'])
        assert len(p2_commissions) == 0


class TestIntegration:
    """End-to-end partner lifecycle."""

    def test_complete_partner_lifecycle(self, clean_db):
        """Full partner journey: signup -> approval -> earn -> payout."""
        # 1. Partner signs up
        partner = create_partner(
            business_id=1,
            name="Success Partner",
            email="success@example.com",
            phone="+91 98765 43210",
            company="Success Corp",
            website="https://success.com",
            tier='reseller',
        )
        assert partner['status'] == PartnerStatus.PENDING

        # 2. Founder approves
        approve_partner(partner['id'], 'founder@example.com')
        partner = get_partner(partner['id'])
        assert partner['status'] == PartnerStatus.APPROVED

        # 3. Partner activates
        activate_partner(partner['id'])
        partner = get_partner(partner['id'])
        assert partner['status'] == PartnerStatus.ACTIVE

        # 4. Track referral activity
        track_click(partner['id'], 'sess_1')
        track_click(partner['id'], 'sess_2')
        track_click(partner['id'], 'sess_3')

        # 5. Customer converts (3 sales)
        for i in range(3):
            record_commission(
                partner_id=partner['id'],
                transaction_id=f'txn_{i}',
                customer_email=f'customer{i}@example.com',
                amount=5000.0,  # Each sale is ₹5000
            )

        # 6. Verify stats
        stats = get_partner_stats(partner['id'])
        assert stats['total_clicks'] == 3
        assert stats['total_conversions'] == 3
        assert stats['conversion_rate'] == 100.0
        assert stats['total_revenue'] == 15000.0
        assert stats['total_earned_commission'] == 3000.0  # 15000 * 0.20

        # 7. Request payout
        payout = request_payout(
            partner_id=partner['id'],
            payout_method='bank_transfer',
            bank_details={
                'account_number': '1234567890',
                'ifsc': 'HDFC0001234',
                'beneficiary_name': 'Success Partner',
            },
        )
        assert payout['total_amount'] == 3000.0
        assert payout['status'] == PayoutStatus.PENDING

        # 8. Process payout
        process_payout(payout['id'], 'transfer_receipt_123')

        # 9. Verify final state
        payouts = get_payouts(partner['id'])
        assert payouts[0]['status'] == PayoutStatus.PROCESSED
        assert payouts[0]['reference_id'] == 'transfer_receipt_123'

        # Stats should reflect paid commission
        stats = get_partner_stats(partner['id'])
        assert stats['total_paid_commission'] == 3000.0
        assert stats['pending_commission'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
