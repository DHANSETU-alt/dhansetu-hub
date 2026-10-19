"""Partner Network Model -- onboarding, commission tracking, payout management.

Tiers:
  - Affiliate: 15% per sale
  - Reseller: 20% per sale + bulk discounts
  - Agency: 25% per sale + dedicated support

Commission calculated on transaction completion, paid monthly (net-30 terms).
Referral tracking via unique URL: https://app.com?partner_id=xxx
"""

import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

from . import db


class PartnerTier:
    """Commission rate definitions per partner tier."""
    AFFILIATE = ('affiliate', 0.15)
    RESELLER = ('reseller', 0.20)
    AGENCY = ('agency', 0.25)

    TIERS = {
        'affiliate': 0.15,
        'reseller': 0.20,
        'agency': 0.25,
    }


class PartnerStatus:
    """Partner lifecycle states."""
    PENDING = 'pending'           # Initial application
    APPROVED = 'approved'         # Founder approved
    ACTIVE = 'active'             # Ready to earn commissions
    SUSPENDED = 'suspended'       # Temporarily inactive
    INACTIVE = 'inactive'         # Permanently disabled


class CommissionStatus:
    """Commission ledger states."""
    EARNED = 'earned'             # Sale completed, commission calculated
    PAID = 'paid'                 # Payout processed
    DISPUTED = 'disputed'         # Under dispute
    REFUNDED = 'refunded'         # Customer refund issued


class PayoutStatus:
    """Payout request states."""
    PENDING = 'pending'            # Awaiting processing
    PROCESSING = 'processing'      # In progress
    PROCESSED = 'processed'        # Complete, funds transferred
    FAILED = 'failed'              # Payment failed


def generate_referral_link(partner_id: int, base_url: str = "https://app.example.com") -> str:
    """Generate unique referral link: https://app.com?partner_id=xxx"""
    return f"{base_url}?partner_id={partner_id}"


def create_partner(
    business_id: int,
    name: str,
    email: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    website: Optional[str] = None,
    tier: str = 'affiliate',
) -> Dict[str, Any]:
    """Create a new partner application.

    Returns dict with partner id and referral link.
    Initial status is 'pending' (requires founder approval).
    """
    if tier not in PartnerTier.TIERS:
        raise ValueError(f"Invalid tier: {tier}. Must be one of {list(PartnerTier.TIERS.keys())}")

    commission_rate = PartnerTier.TIERS[tier]

    with db.get_conn() as conn:
        cursor = conn.cursor()

        # Check email uniqueness
        cursor.execute("SELECT id FROM partners WHERE email = ?", (email,))
        if cursor.fetchone():
            raise ValueError(f"Email {email} already registered as partner")

        # Generate referral link (will use partner_id once created)
        referral_link = secrets.token_urlsafe(12)
        referral_link = f"ref_{referral_link}"

        cursor.execute("""
            INSERT INTO partners (
                business_id, name, email, phone, company, website,
                tier, commission_rate, referral_link, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (business_id, name, email, phone, company, website, tier, commission_rate, referral_link, PartnerStatus.PENDING))

        partner_id = cursor.lastrowid

        # Initialize partner stats
        cursor.execute("""
            INSERT INTO partner_stats (partner_id)
            VALUES (?)
        """, (partner_id,))

        return {
            'id': partner_id,
            'name': name,
            'email': email,
            'tier': tier,
            'commission_rate': commission_rate,
            'referral_link': generate_referral_link(partner_id),
            'status': PartnerStatus.PENDING,
        }


def get_partner(partner_id: int) -> Optional[Dict[str, Any]]:
    """Fetch partner details."""
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, business_id, name, email, phone, company, website,
                   tier, status, commission_rate, referral_link,
                   approved_by, approved_at, created_at, updated_at
            FROM partners
            WHERE id = ?
        """, (partner_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'business_id': row[1],
            'name': row[2],
            'email': row[3],
            'phone': row[4],
            'company': row[5],
            'website': row[6],
            'tier': row[7],
            'status': row[8],
            'commission_rate': row[9],
            'referral_link': row[10],
            'approved_by': row[11],
            'approved_at': row[12],
            'created_at': row[13],
            'updated_at': row[14],
        }


def get_partner_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch partner by email address."""
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, business_id, name, email, phone, company, website,
                   tier, status, commission_rate, referral_link,
                   approved_by, approved_at, created_at, updated_at
            FROM partners
            WHERE email = ?
        """, (email,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'business_id': row[1],
            'name': row[2],
            'email': row[3],
            'phone': row[4],
            'company': row[5],
            'website': row[6],
            'tier': row[7],
            'status': row[8],
            'commission_rate': row[9],
            'referral_link': row[10],
            'approved_by': row[11],
            'approved_at': row[12],
            'created_at': row[13],
            'updated_at': row[14],
        }


def approve_partner(partner_id: int, approved_by: str) -> bool:
    """Founder approves a partner application (pending -> approved)."""
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE partners
            SET status = ?, approved_by = ?, approved_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (PartnerStatus.APPROVED, approved_by, datetime.utcnow().isoformat(), partner_id))
        return cursor.rowcount > 0


def activate_partner(partner_id: int) -> bool:
    """Activate an approved partner (approved -> active). Ready to earn commissions."""
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE partners
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status IN (?, ?)
        """, (PartnerStatus.ACTIVE, partner_id, PartnerStatus.APPROVED, PartnerStatus.SUSPENDED))
        return cursor.rowcount > 0


def record_commission(
    partner_id: int,
    transaction_id: str,
    customer_email: str,
    amount: float,
    product: str = '',
) -> Dict[str, Any]:
    """Record a sale commission when transaction completes.

    Commission amount is calculated: amount * commission_rate
    Status is 'earned' (becomes 'paid' after payout processes).
    """
    with db.get_conn() as conn:
        cursor = conn.cursor()

        # Get partner's commission rate
        cursor.execute("SELECT commission_rate FROM partners WHERE id = ?", (partner_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Partner {partner_id} not found")

        commission_rate = row[0]
        commission_amount = amount * commission_rate

        cursor.execute("""
            INSERT INTO partner_commissions (
                partner_id, transaction_id, customer_email, amount,
                commission_rate, commission_amount, product, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            partner_id, transaction_id, customer_email, amount,
            commission_rate, commission_amount, product, CommissionStatus.EARNED
        ))

        commission_id = cursor.lastrowid

        # Update partner stats
        _update_partner_stats(conn, partner_id)

        return {
            'id': commission_id,
            'partner_id': partner_id,
            'transaction_id': transaction_id,
            'amount': amount,
            'commission_rate': commission_rate,
            'commission_amount': commission_amount,
            'status': CommissionStatus.EARNED,
        }


def get_commissions(
    partner_id: int,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Get commission history for a partner."""
    with db.get_conn() as conn:
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT id, partner_id, transaction_id, customer_email, amount,
                       commission_rate, commission_amount, product, status,
                       paid_date, created_at
                FROM partner_commissions
                WHERE partner_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (partner_id, status, limit, offset))
        else:
            cursor.execute("""
                SELECT id, partner_id, transaction_id, customer_email, amount,
                       commission_rate, commission_amount, product, status,
                       paid_date, created_at
                FROM partner_commissions
                WHERE partner_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (partner_id, limit, offset))

        return [
            {
                'id': row[0],
                'partner_id': row[1],
                'transaction_id': row[2],
                'customer_email': row[3],
                'amount': row[4],
                'commission_rate': row[5],
                'commission_amount': row[6],
                'product': row[7],
                'status': row[8],
                'paid_date': row[9],
                'created_at': row[10],
            }
            for row in cursor.fetchall()
        ]


def get_partner_stats(partner_id: int) -> Optional[Dict[str, Any]]:
    """Get partner performance stats (clicks, conversions, revenue)."""
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, partner_id, total_clicks, total_conversions, conversion_rate,
                   total_revenue, total_earned_commission, total_paid_commission,
                   pending_commission, last_updated
            FROM partner_stats
            WHERE partner_id = ?
        """, (partner_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'id': row[0],
            'partner_id': row[1],
            'total_clicks': row[2],
            'total_conversions': row[3],
            'conversion_rate': row[4],
            'total_revenue': row[5],
            'total_earned_commission': row[6],
            'total_paid_commission': row[7],
            'pending_commission': row[8],
            'last_updated': row[9],
        }


def _update_partner_stats(conn: sqlite3.Connection, partner_id: int) -> None:
    """Recalculate and cache partner stats (called after commission changes)."""
    cursor = conn.cursor()

    # Total earned (all commissions with status != 'refunded')
    cursor.execute("""
        SELECT COALESCE(SUM(commission_amount), 0)
        FROM partner_commissions
        WHERE partner_id = ? AND status != ?
    """, (partner_id, CommissionStatus.REFUNDED))
    total_earned = cursor.fetchone()[0]

    # Total paid
    cursor.execute("""
        SELECT COALESCE(SUM(commission_amount), 0)
        FROM partner_commissions
        WHERE partner_id = ? AND status = ?
    """, (partner_id, CommissionStatus.PAID))
    total_paid = cursor.fetchone()[0]

    pending = total_earned - total_paid

    # Total conversions
    cursor.execute("""
        SELECT COUNT(DISTINCT transaction_id)
        FROM partner_commissions
        WHERE partner_id = ?
    """, (partner_id,))
    total_conversions = cursor.fetchone()[0]

    # Total revenue from commissions
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM partner_commissions
        WHERE partner_id = ?
    """, (partner_id,))
    total_revenue = cursor.fetchone()[0]

    conversion_rate = 0.0
    cursor.execute("SELECT total_clicks FROM partner_stats WHERE partner_id = ?", (partner_id,))
    row = cursor.fetchone()
    if row and row[0]:
        conversion_rate = (total_conversions / row[0]) * 100

    cursor.execute("""
        UPDATE partner_stats
        SET total_conversions = ?, conversion_rate = ?, total_revenue = ?,
            total_earned_commission = ?, total_paid_commission = ?,
            pending_commission = ?, last_updated = CURRENT_TIMESTAMP
        WHERE partner_id = ?
    """, (
        total_conversions, conversion_rate, total_revenue,
        total_earned, total_paid, pending, partner_id
    ))


def request_payout(
    partner_id: int,
    payout_method: str,
    bank_details: Optional[Dict] = None,
    upi_id: Optional[str] = None,
    paypal_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Partner requests payout for earned commissions.

    Criteria:
      - Earned commission >= ₹100
      - No payout request pending
      - At least 30 days since last payout (net-30 terms)
    """
    with db.get_conn() as conn:
        cursor = conn.cursor()

        # Get pending commission
        cursor.execute("""
            SELECT COALESCE(SUM(commission_amount), 0)
            FROM partner_commissions
            WHERE partner_id = ? AND status = ?
        """, (partner_id, CommissionStatus.EARNED))
        pending_commission = cursor.fetchone()[0]

        if pending_commission < 100:
            raise ValueError(f"Minimum payout amount is ₹100. Current pending: ₹{pending_commission}")

        # Check for existing pending payout
        cursor.execute("""
            SELECT id FROM partner_payouts
            WHERE partner_id = ? AND status = ?
        """, (partner_id, PayoutStatus.PENDING))
        if cursor.fetchone():
            raise ValueError("Payout request already pending for this partner")

        # Insert payout request
        period_end = datetime.utcnow().date()
        period_start = period_end - timedelta(days=30)

        bank_details_json = json.dumps(bank_details) if bank_details else None

        cursor.execute("""
            INSERT INTO partner_payouts (
                partner_id, total_amount, payout_method, bank_details,
                upi_id, paypal_email, period_start, period_end, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            partner_id, pending_commission, payout_method, bank_details_json,
            upi_id, paypal_email, period_start, period_end, PayoutStatus.PENDING
        ))

        payout_id = cursor.lastrowid

        return {
            'id': payout_id,
            'partner_id': partner_id,
            'total_amount': pending_commission,
            'payout_method': payout_method,
            'status': PayoutStatus.PENDING,
        }


def process_payout(payout_id: int, reference_id: str) -> bool:
    """Mark payout as processed and update commission status to 'paid'."""
    with db.get_conn() as conn:
        cursor = conn.cursor()

        # Get payout details
        cursor.execute("""
            SELECT partner_id, total_amount
            FROM partner_payouts
            WHERE id = ?
        """, (payout_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Payout {payout_id} not found")

        partner_id, total_amount = row

        # Mark commissions as paid (up to payout amount)
        cursor.execute("""
            UPDATE partner_commissions
            SET status = ?, paid_date = CURRENT_TIMESTAMP
            WHERE partner_id = ? AND status = ?
            ORDER BY created_at ASC
            LIMIT (
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM partner_commissions
                    WHERE partner_id = ? AND status = ?
                    ORDER BY created_at ASC
                ) WHERE commission_amount <= ?
            )
        """, (
            CommissionStatus.PAID, partner_id, CommissionStatus.EARNED,
            partner_id, CommissionStatus.EARNED, total_amount
        ))

        # Mark payout as processed
        cursor.execute("""
            UPDATE partner_payouts
            SET status = ?, processed_date = CURRENT_TIMESTAMP, reference_id = ?
            WHERE id = ?
        """, (PayoutStatus.PROCESSED, reference_id, payout_id))

        # Update stats
        _update_partner_stats(conn, partner_id)

        return True


def get_payouts(
    partner_id: int,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get payout history for a partner."""
    with db.get_conn() as conn:
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT id, partner_id, total_amount, currency, payout_method,
                       period_start, period_end, status, processed_date, reference_id, created_at
                FROM partner_payouts
                WHERE partner_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (partner_id, status, limit))
        else:
            cursor.execute("""
                SELECT id, partner_id, total_amount, currency, payout_method,
                       period_start, period_end, status, processed_date, reference_id, created_at
                FROM partner_payouts
                WHERE partner_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (partner_id, limit))

        return [
            {
                'id': row[0],
                'partner_id': row[1],
                'total_amount': row[2],
                'currency': row[3],
                'payout_method': row[4],
                'period_start': row[5],
                'period_end': row[6],
                'status': row[7],
                'processed_date': row[8],
                'reference_id': row[9],
                'created_at': row[10],
            }
            for row in cursor.fetchall()
        ]


def track_click(partner_id: int, session_id: str = '') -> int:
    """Track a referral link click."""
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO referral_clicks (partner_id, session_id)
            VALUES (?, ?)
        """, (partner_id, session_id))

        click_id = cursor.lastrowid

        # Update click count
        cursor.execute("""
            UPDATE partner_stats
            SET total_clicks = total_clicks + 1
            WHERE partner_id = ?
        """, (partner_id,))

        return click_id
