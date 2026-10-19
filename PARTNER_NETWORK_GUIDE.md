# Partner Network System — Track B Feature 2

Complete guide to onboarding, tracking commissions, managing payouts, and analyzing referral performance.

## Overview

The Partner Network enables customers to earn recurring revenue by referring buyers. Three tiers offer tiered incentives:

- **Affiliate**: 15% per sale, basic analytics
- **Reseller**: 20% per sale, bulk discounts, performance dashboard
- **Agency**: 25% per sale, priority support, advanced analytics

Commission is calculated when a transaction completes (status: "earned"). Payouts process monthly under net-30 terms: earned commissions become eligible for withdrawal 30 days after earning.

---

## Core Concepts

### Partner Lifecycle

1. **Application (Pending)**: Partner self-registers with name, email, tier choice
2. **Approval**: Founder reviews and approves/rejects applications
3. **Activation**: Approved partner transitions to "active" and begins earning
4. **Commission Earning**: Sales attributed to partner's referral link are tracked
5. **Payout**: Partner requests payout once earned >= ₹100; founder processes

### Commission Status States

- **earned**: Sale completed, commission calculated, awaiting 30-day hold
- **paid**: Commission transferred to partner via payout
- **disputed**: Under review/investigation
- **refunded**: Customer refund issued, commission reversed

### Payout Status States

- **pending**: Partner submitted request, awaiting approval
- **processing**: Founder processing the payment
- **processed**: Payment transferred, with receipt reference
- **failed**: Payment attempt failed

---

## Database Schema

### Partners Table
Stores partner profile and metadata.

```sql
CREATE TABLE partners (
  id INTEGER PRIMARY KEY,
  business_id INTEGER,
  name TEXT,
  email TEXT UNIQUE,              -- login identity
  phone TEXT,
  company TEXT,
  website TEXT,
  tier TEXT,                      -- affiliate | reseller | agency
  status TEXT,                    -- pending | approved | active | suspended | inactive
  commission_rate REAL,           -- 0.15-0.25, set by tier
  referral_link TEXT UNIQUE,      -- https://app.com?partner_id=xxx
  approved_by TEXT,
  approved_at TEXT,
  created_at TEXT,
  updated_at TEXT
);
```

### Partner Commissions Table
Ledger of all sales attributed to partners.

```sql
CREATE TABLE partner_commissions (
  id INTEGER PRIMARY KEY,
  partner_id INTEGER,
  transaction_id TEXT UNIQUE,     -- gateway payment ID
  customer_email TEXT,
  amount REAL,                    -- sale amount
  commission_rate REAL,           -- rate at time of sale
  commission_amount REAL,         -- calculated amount
  product TEXT,
  status TEXT,                    -- earned | paid | disputed | refunded
  paid_date TEXT,
  created_at TEXT
);
```

### Partner Payouts Table
Records payout requests and processing.

```sql
CREATE TABLE partner_payouts (
  id INTEGER PRIMARY KEY,
  partner_id INTEGER,
  total_amount REAL,
  currency TEXT DEFAULT 'INR',
  payout_method TEXT,            -- bank_transfer | paypal | upi
  bank_details TEXT,             -- JSON
  upi_id TEXT,
  paypal_email TEXT,
  period_start TEXT,             -- YYYY-MM-DD
  period_end TEXT,
  status TEXT,                   -- pending | processing | processed | failed
  processed_date TEXT,
  reference_id TEXT,             -- receipt/confirmation
  created_at TEXT
);
```

### Partner Stats Table
Cached aggregates for dashboard performance.

```sql
CREATE TABLE partner_stats (
  id INTEGER PRIMARY KEY,
  partner_id INTEGER UNIQUE,
  total_clicks INTEGER,
  total_conversions INTEGER,
  conversion_rate REAL,
  total_revenue REAL,
  total_earned_commission REAL,
  total_paid_commission REAL,
  pending_commission REAL,
  last_updated TEXT
);
```

### Referral Clicks Table
Track each referral link click for analytics.

```sql
CREATE TABLE referral_clicks (
  id INTEGER PRIMARY KEY,
  partner_id INTEGER,
  referrer_url TEXT,
  user_agent TEXT,
  ip_address TEXT,
  session_id TEXT,
  converted INTEGER,             -- 0/1
  created_at TEXT
);
```

---

## API Routes

All routes prefix `/api/partners/`.

### POST `/apply`
**Partner Application Submission**

Submit a new partner application.

**Request:**
```json
{
  "business_id": 1,
  "name": "John Reseller",
  "email": "john@example.com",
  "phone": "+91 98765 43210",
  "company": "Reseller Corp",
  "website": "https://reseller.com",
  "tier": "affiliate"
}
```

**Response (201):**
```json
{
  "id": 42,
  "name": "John Reseller",
  "email": "john@example.com",
  "tier": "affiliate",
  "commission_rate": 0.15,
  "referral_link": "https://app.example.com?partner_id=42",
  "status": "pending"
}
```

**Errors:**
- `400`: Missing required fields
- `400`: Invalid tier
- `400`: Email already registered

---

### GET `/dashboard`
**Partner Dashboard Data**

Retrieve dashboard summary (commissions, payouts, stats).

**Query:**
- `email`: Partner email (required)

**Response:**
```json
{
  "partner": {
    "id": 42,
    "name": "John Reseller",
    "email": "john@example.com",
    "tier": "affiliate",
    "status": "active",
    "commission_rate": 0.15,
    "referral_link": "https://app.example.com?partner_id=42"
  },
  "stats": {
    "total_clicks": 150,
    "total_conversions": 15,
    "conversion_rate": 10.0,
    "total_revenue": 75000,
    "total_earned_commission": 11250,
    "total_paid_commission": 10500,
    "pending_commission": 750
  },
  "recent_commissions": [
    {
      "id": 1,
      "transaction_id": "txn_123",
      "amount": 5000,
      "commission_amount": 750,
      "status": "earned",
      "created_at": "2026-10-01T10:00:00Z"
    }
  ],
  "recent_payouts": [
    {
      "id": 1,
      "total_amount": 10500,
      "status": "processed",
      "processed_date": "2026-09-30T15:00:00Z"
    }
  ]
}
```

---

### GET `/commissions`
**Commission History with Filters**

Retrieve paginated commission ledger.

**Query:**
- `email`: Partner email (required)
- `status`: Filter by status (earned|paid|disputed|refunded)
- `limit`: Max results (default: 100)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "commissions": [
    {
      "id": 1,
      "transaction_id": "txn_123",
      "customer_email": "buyer@example.com",
      "amount": 5000,
      "commission_rate": 0.15,
      "commission_amount": 750,
      "product": "Premium Plan",
      "status": "earned",
      "paid_date": null,
      "created_at": "2026-10-01T10:00:00Z"
    }
  ],
  "total": 15
}
```

---

### POST `/payout-request`
**Request Payout for Earned Commissions**

Create a payout request.

**Criteria:**
- Earned commission >= ₹100
- No pending payout request
- 30+ days since last payout (net-30 terms)

**Request:**
```json
{
  "email": "john@example.com",
  "payout_method": "bank_transfer",
  "bank_details": {
    "account_number": "1234567890",
    "ifsc": "HDFC0001234",
    "beneficiary_name": "John Reseller"
  }
}
```

**Alternative methods:**
```json
{
  "email": "john@example.com",
  "payout_method": "upi",
  "upi_id": "john@hdfc"
}
```

```json
{
  "email": "john@example.com",
  "payout_method": "paypal",
  "paypal_email": "john@paypal.com"
}
```

**Response (201):**
```json
{
  "id": 5,
  "partner_id": 42,
  "total_amount": 11250,
  "payout_method": "bank_transfer",
  "status": "pending"
}
```

**Errors:**
- `400`: Minimum ₹100 earned required
- `400`: Payout request already pending
- `400`: Missing method-specific fields

---

### GET `/referral-link`
**Get Unique Referral Link and Share URLs**

Retrieve partner's referral link and pre-filled share URLs.

**Query:**
- `email`: Partner email (required)

**Response:**
```json
{
  "referral_link": "https://app.example.com?partner_id=42",
  "tracking_param": "partner_id=42",
  "share_text": "Earn 15% commission when you refer customers to our platform!",
  "share_urls": {
    "twitter": "https://twitter.com/intent/tweet?text=...",
    "linkedin": "https://www.linkedin.com/sharing/share-offsite/?url=...",
    "whatsapp": "https://wa.me/?text=...",
    "email": "mailto:?subject=...&body=..."
  }
}
```

---

### GET `/stats`
**Referral Performance Stats**

Comprehensive analytics dashboard.

**Query:**
- `email`: Partner email (required)
- `period`: Time range (day|week|month|all, default: all)

**Response:**
```json
{
  "total_clicks": 150,
  "total_conversions": 15,
  "conversion_rate": 10.0,
  "total_revenue": 75000,
  "total_earned_commission": 11250,
  "total_paid_commission": 10500,
  "pending_commission": 750,
  "period_start": "2026-01-01",
  "period_end": "2026-10-01",
  "top_products": [
    {
      "product": "Premium Plan",
      "count": 8,
      "revenue": 40000
    },
    {
      "product": "Pro Plan",
      "count": 7,
      "revenue": 35000
    }
  ]
}
```

---

## Python API (Orchestrator)

Import and use the model directly:

```python
from orchestrator.partner_network_model import (
    create_partner,
    approve_partner,
    activate_partner,
    record_commission,
    request_payout,
    process_payout,
    get_partner_stats,
)

# Create partner application
partner = create_partner(
    business_id=1,
    name="John Reseller",
    email="john@example.com",
    tier='affiliate',
)

# Founder approves
approve_partner(partner['id'], approved_by='founder@example.com')

# Activate
activate_partner(partner['id'])

# Record sale commission (when payment gateway reports)
commission = record_commission(
    partner_id=partner['id'],
    transaction_id='razorpay_pay_123',
    customer_email='buyer@example.com',
    amount=5000.0,
    product='Premium Plan',
)

# Get stats
stats = get_partner_stats(partner['id'])
print(f"Earned: ₹{stats['total_earned_commission']}")
print(f"Conversion rate: {stats['conversion_rate']}%")

# Partner requests payout
payout = request_payout(
    partner_id=partner['id'],
    payout_method='bank_transfer',
    bank_details={
        'account_number': '1234567890',
        'ifsc': 'HDFC0001234',
        'beneficiary_name': 'John Reseller',
    },
)

# Founder processes payout
process_payout(payout['id'], reference_id='transfer_receipt_123')
```

---

## Frontend Implementation

### Partner Network Workspace

Located at `/partner-network`:

1. **Dashboard Tab**
   - Partner email lookup
   - Stats cards (clicks, conversions, revenue, pending commission)
   - Three sub-tabs:
     - **Referral Link**: Unique tracking URL + social share buttons
     - **Commissions**: Ledger of all tracked sales
     - **Payouts**: History of payout requests and status

2. **Apply Tab**
   - Tier selection (Affiliate/Reseller/Agency)
   - Application form (name, email, phone, company, website)
   - Next steps checklist

3. **Resources Tab**
   - Commission guide
   - Marketing materials (templates, copy, graphics)
   - Analytics deep dive
   - Support & FAQ

### Key UI Components

- **Stats Cards**: Real-time aggregates from `partner_stats` table
- **Commission Table**: Sortable ledger with status filtering
- **Payout Request Form**: Method selection (bank/UPI/PayPal) + method-specific fields
- **Referral Link Display**: Copy-to-clipboard + pre-filled social shares

---

## Referral Tracking

### How It Works

1. **Unique Link Per Partner**: Each partner gets `https://app.com?partner_id=xxx`
2. **Click Attribution**: When link is clicked, session is tagged with `partner_id`
3. **Conversion Tracking**: When customer completes purchase, payment gateway includes `partner_id`
4. **Commission Auto-Calculation**: On payment confirmation, commission recorded with tier rate

### Linking Payment to Referral

When payment gateway reports a completed transaction:

```python
# Payment processor webhook
transaction_data = {
    'payment_id': 'razorpay_pay_123',
    'amount': 5000,
    'customer_email': 'buyer@example.com',
    'metadata': {
        'partner_id': 42,  # From URL param during signup
    }
}

# Record commission
from orchestrator.partner_network_model import record_commission
record_commission(
    partner_id=transaction_data['metadata']['partner_id'],
    transaction_id=transaction_data['payment_id'],
    customer_email=transaction_data['customer_email'],
    amount=transaction_data['amount'],
)
```

---

## Testing

Run tests with:

```bash
pytest tests/test_partner_network.py -v
```

**Coverage:**
- Partner onboarding (signup → approval → activation)
- Commission calculation (tier rates, accuracy)
- Referral tracking (clicks, conversions, stats)
- Payout processing (requests, processing, status)
- Permission checks (partner data isolation)
- Full lifecycle (end-to-end integration)

---

## Deployment Checklist

- [ ] Database schema applied (schema.sql with partner tables)
- [ ] Orchestrator model (`orchestrator/partner_network_model.py`) deployed
- [ ] API routes (`dashboard/app/api/partners/*/route.ts`) running
- [ ] Frontend workspace (`dashboard/app/partner-network/page.tsx`) live
- [ ] Payment gateway wired to record commissions (webhook integration)
- [ ] Tests passing (all 50+ test cases)
- [ ] Partner dashboard verified in browser
- [ ] Founder can approve/reject applications
- [ ] Payout processing integrated with bank/UPI/PayPal
- [ ] Analytics real-time on stats dashboard

---

## Commission Calculation Formula

```
commission_amount = sale_amount × commission_rate

Where commission_rate =
  0.15 (15%) for tier='affiliate'
  0.20 (20%) for tier='reseller'
  0.25 (25%) for tier='agency'
```

Example:
- Sale: ₹5,000
- Tier: Affiliate (15%)
- Commission: ₹5,000 × 0.15 = ₹750

---

## Payout Net-30 Terms

Commissions become eligible for payout 30 days after earning:

```
earned_date: 2026-09-01
eligible_date: 2026-10-01 (earned_date + 30 days)
payout_window: 2026-10-01 onwards
```

Payouts are processed manually by founder on demand once eligible.

---

## FAQ

**Q: When can a partner request payout?**
A: Once earned commission >= ₹100 and at least 30 days have passed since earning (net-30 terms).

**Q: What happens if a customer requests a refund?**
A: Commission status moves to "refunded" and is deducted from pending/total earned amounts.

**Q: Can partners change tiers?**
A: Tier changes require new application. Existing tier rate locked at time of sale.

**Q: How are clicks tracked?**
A: Referral link includes `partner_id` parameter. Click is logged when parameter detected.

**Q: Is conversion tracking automatic?**
A: Yes, payment gateway webhook triggers commission recording. Requires `partner_id` in order metadata.

---

## Related

- Payment Gateway Integration: See `orchestrator/payment_gateway_manager.py`
- Founder Dashboard: See `dashboard/app/`
- Schema: See `db/schema.sql`
