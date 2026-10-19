# Razorpay Payment Integration - Task #6

Complete production-ready Razorpay payment integration with on-page Checkout.js, webhook handling, signature verification, and database persistence.

## Architecture Overview

```
┌─────────────────┐
│  Frontend       │
│  (RazorpayCheckout.tsx)
└────────┬────────┘
         │ 1. POST /api/blackboxops/razorpay-order
         │    (customer info)
         ▼
┌─────────────────────────────────────────┐
│  Next.js API Route (razorpay-order)     │
│  - Validates input                      │
│  - Calls Python CLI: --create-razorpay-order
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Python CLI (orchestrator/cli.py)       │
│  - Validates product pricing caps       │
│  - Calls payment_gateway_manager        │
│  - Inserts payment_transactions record  │
│  - Returns order_id to frontend         │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Razorpay Orders API                    │
│  - Creates order in Razorpay account    │
│  - Returns order_id, amount, currency   │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Frontend - Razorpay Checkout Modal     │
│  (Checkout.js SDK - browser-native)     │
│  - Displays checkout form               │
│  - Customer enters payment details      │
│  - Processes payment through Razorpay   │
│  - Returns: order_id|payment_id         │
└────────┬────────────────────────────────┘
         │
         ├─ 2. POST /api/blackboxops/razorpay-verify
         │      (orderId, paymentId, signature)
         │
         ▼
┌─────────────────────────────────────────┐
│  Next.js API Route (razorpay-verify)    │
│  - Verifies client signature            │
│  - Calls CLI: --verify-razorpay-payment│
│  - Updates DB status: created->paid     │
└─────────────────────────────────────────┘
         │
         └─ Concurrent: Razorpay Webhook ──┐
                                            │
                                            ▼
                        ┌──────────────────────────────────┐
                        │  POST /api/blackboxops/razorpay- │
                        │  webhook (x-razorpay-signature)  │
                        │                                  │
                        │  - Verifies HMAC signature       │
                        │  - Processes real webhook        │
                        │  - Handles: payment.captured,    │
                        │    order.paid, payment.failed    │
                        │  - Idempotent: same event twice  │
                        │    updates same record, never     │
                        │    creates duplicate             │
                        │  - Updates DB status             │
                        │  - Returns 200 OK                │
                        └──────────────────────────────────┘
```

## Components

### 1. Backend Database Layer

**File**: `orchestrator/db.py`

```python
# Added customer_email column to payment_transactions table
def _migrate_payment_transaction_columns(conn):
    # Migrates customer_email column if not present
    # Idempotent - safe to run multiple times
    
# Enhanced insert_payment_transaction() accepts customer_email
def insert_payment_transaction(conn, gateway, gateway_ref, amount, currency,
                                description, customer_name=None, 
                                customer_contact=None, customer_email=None, ...):
    # Stores complete transaction with email for follow-up
```

**Schema**:
```sql
CREATE TABLE payment_transactions (
  id INTEGER PRIMARY KEY,
  gateway TEXT,           -- razorpay_order | stripe_checkout | upi
  gateway_ref TEXT,       -- Razorpay order_id
  payment_id TEXT,        -- Razorpay payment_id (from webhook)
  amount REAL,
  currency TEXT,
  description TEXT,
  customer_name TEXT,
  customer_contact TEXT,
  customer_email TEXT,    -- NEW: for email follow-ups
  status TEXT,            -- created | paid | failed
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Backend Payment Gateway

**File**: `orchestrator/payment_gateway_manager.py`

Three core functions (already existed, verified working):

```python
def create_razorpay_order(key_id, key_secret, amount_inr, receipt):
    # Creates real Razorpay order
    # Returns: order_id, amount (paise), currency
    
def verify_razorpay_webhook_signature(raw_body, signature, webhook_secret):
    # HMAC-SHA256 verification
    # Uses constant-time comparison (hmac.compare_digest)
    # Signature covers EXACT raw bytes Razorpay sent
    
def verify_razorpay_checkout_signature(key_secret, order_id, payment_id, signature):
    # Verifies client-side checkout success claim
    # Signature = HMAC-SHA256("order_id|payment_id")
```

### 3. Python CLI

**File**: `orchestrator/cli.py`

Three commands for order lifecycle:

```bash
# 1. Create order
python3 -m orchestrator.cli --create-razorpay-order \
    --razorpay-key-id KEY --razorpay-key-secret SECRET \
    --product blackboxops_os_starter --receipt order_12345

# 2. Verify client checkout callback
python3 -m orchestrator.cli --verify-razorpay-payment \
    --razorpay-key-secret SECRET \
    --order-id order_abc123 \
    --payment-id pay_def456 \
    --razorpay-signature signature_hex

# 3. Process webhook (server-to-server from Razorpay)
python3 -m orchestrator.cli --process-razorpay-webhook \
    --webhook-secret WEBHOOK_SECRET \
    --raw-body '{"event":"payment.captured",...}' \
    --razorpay-signature signature_hex
```

### 4. Next.js API Routes

#### Route: `/api/blackboxops/razorpay-order`

**File**: `dashboard/app/api/blackboxops/razorpay-order/route.ts`

Creates orders with customer info:

```typescript
POST /api/blackboxops/razorpay-order
{
  "product": "blackboxops_os_starter",
  "customerName": "John Doe",        // optional
  "customerEmail": "john@example.com", // optional
  "customerContact": "+919876543210"   // optional
}

Response:
{
  "order_id": "order_abc123",
  "amount": 29900,           // paise (integer)
  "currency": "INR",
  "keyId": "rzp_live_...",   // Razorpay public key
  "raw": { ... }
}
```

#### Route: `/api/blackboxops/razorpay-verify`

**File**: `dashboard/app/api/blackboxops/razorpay-verify/route.ts`

Verifies client-side checkout callback:

```typescript
POST /api/blackboxops/razorpay-verify
{
  "orderId": "order_abc123",
  "paymentId": "pay_def456",
  "signature": "signature_hex"  // from Checkout.js callback
}

Response:
{
  "verified": true,
  "transaction": { order_id, status: "paid", ... }
}
```

#### Route: `/api/blackboxops/razorpay-webhook`

**File**: `dashboard/app/api/blackboxops/razorpay-webhook/route.ts`

Handles Razorpay webhooks (server-to-server):

```typescript
POST /api/blackboxops/razorpay-webhook
Header: x-razorpay-signature: signature_hex
Header: x-razorpay-event-id: evt_... (idempotency key)

Body (raw JSON):
{
  "event": "payment.captured" | "payment.failed" | "order.paid",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_...",
        "order_id": "order_abc123",
        "status": "captured",
        "amount": 29900
      }
    }
  }
}

Response:
{
  "verified": true,
  "event": "payment.captured",
  "order_id": "order_abc123",
  "payment_id": "pay_...",
  "updated_status": "paid",
  "processed": true
}
```

### 5. Frontend Checkout Component

**File**: `dashboard/components/RazorpayCheckout.tsx`

Drop-in React component for checkout:

```typescript
import { RazorpayCheckout } from "@/components/RazorpayCheckout";

export default function ProductPage() {
  return (
    <RazorpayCheckout
      product="blackboxops_os_starter"
      amount={299}
      description="BlackboxOps Starter Edition"
      onPaymentSuccess={(response) => {
        console.log("Payment successful:", response);
        // Redirect, show confirmation, etc.
      }}
      onPaymentFailure={(error) => {
        console.error("Payment failed:", error);
      }}
    />
  );
}
```

**Features**:
- Loads Razorpay Checkout.js SDK dynamically
- Email validation (required)
- Optional: customer name, phone
- Real-time error display
- Loading state management
- Constant-time signature verification
- Handles payment cancellation

## Security Implementation

### 1. Webhook Signature Verification (Production-Critical)

```python
import hashlib
import hmac

def verify_razorpay_webhook_signature(raw_body: bytes, signature: str, 
                                      webhook_secret: str) -> bool:
    expected = hmac.new(webhook_secret.encode(), raw_body, 
                       hashlib.sha256).hexdigest()
    # CRITICAL: Constant-time comparison prevents timing attacks
    return hmac.compare_digest(expected, signature)
```

**Why this matters**:
- Razorpay is sending real money movement notifications
- A forged webhook could claim payments that never happened
- Timing-safe comparison prevents attackers from guessing secrets byte-by-byte

### 2. Client-Side Checkout Signature Verification

```python
def verify_razorpay_checkout_signature(key_secret: str, order_id: str, 
                                       payment_id: str, signature: str) -> bool:
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(key_secret.encode(), payload, 
                       hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**Why this matters**:
- Checkout.js runs entirely in customer's browser
- Browser can be inspected/manipulated with dev tools
- An attacker could claim success for unpaid orders
- Server-side verification is the actual security boundary

### 3. Idempotent Webhook Processing

**Problem**: Razorpay retries webhooks that don't return 2xx
**Solution**: Database unique index prevents duplicate processing

```python
# payment_transactions(gateway, gateway_ref) is UNIQUE
# WHERE gateway_ref IS NOT NULL

# First webhook: payment.captured
UPDATE payment_transactions 
SET status = 'paid' 
WHERE gateway_ref = 'order_abc123'

# Duplicate webhook (retry): same event
UPDATE payment_transactions 
SET status = 'paid'  # Same update, same row
WHERE gateway_ref = 'order_abc123'

# Result: idempotent - no duplicate row created
```

### 4. Raw Body Signature Verification

**Critical mistake to avoid**:
```python
# WRONG - JSON re-serialization breaks signature
event = json.loads(req.text())
signature_check(json.dumps(event), ...)  # Different bytes!

# CORRECT - Use exact raw bytes received
raw_body = await req.text().encode()
signature_check(raw_body, ...)  # Same bytes Razorpay sent
```

Even a single space/newline difference breaks the HMAC.

## Configuration

### Environment Variables

```bash
# Razorpay API credentials (from https://dashboard.razorpay.com/app/keys)
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxxx    # Public key
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxx # Secret key

# Razorpay Webhook Secret 
# (different from Key Secret, set in dashboard at Webhooks)
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxxx
```

### Webhook Configuration (In Razorpay Dashboard)

1. Go to Dashboard → Settings → API Keys → Webhooks
2. Add webhook endpoint: `https://yoursite.com/api/blackboxops/razorpay-webhook`
3. Subscribe to events:
   - `payment.captured` - Payment succeeded
   - `payment.failed` - Payment declined
   - `order.paid` - Alternative success event
4. Copy Webhook Secret, set as `RAZORPAY_WEBHOOK_SECRET` env var

## Database Lifecycle

### Flow: Order Creation

```
1. Frontend: POST /razorpay-order {product, email}
   ↓
2. API: Validates, calls Python CLI
   ↓
3. CLI: Validates product pricing cap, calls API
   ↓
4. API Response: Returns order_id (not persisted yet)
   ↓
5. CLI: INSERT payment_transactions (status='created')
   ↓
6. DB: Row inserted, awaiting payment
```

### Flow: Payment Confirmation

```
Two parallel paths (webhook is authoritative):

Path 1: Client-side verification (immediate feedback)
  1. Frontend: POST /razorpay-verify {orderId, paymentId, signature}
  2. API: Verifies signature, calls CLI
  3. CLI: UPDATE payment_transactions status='paid'
  4. DB: Status updated immediately
  5. Frontend: Show success page

Path 2: Server-to-server webhook (bank-final confirmation)
  1. Razorpay: POST /razorpay-webhook {event, payload, signature}
  2. API: Verifies HMAC signature
  3. CLI: Parses event, matches order_id
  4. CLI: UPDATE payment_transactions status='paid'
  5. DB: Status confirmed (idempotent on retry)
```

**Both paths update same row** → Single source of truth

### Flow: Payment Failure

```
1. Customer declines payment in Checkout modal
  ↓
2. Frontend: payment.handler() fails
  ↓
3. Razorpay: POST /webhook {event: "payment.failed", ...}
  ↓
4. API: Verifies, calls CLI
  ↓
5. CLI: UPDATE payment_transactions status='failed'
  ↓
6. DB: Order marked failed, retry available
```

## Testing

**Run all payment integration tests**:

```bash
python3 -m pytest tests/test_razorpay_checkout_flow.py -v

# All 17 tests pass:
# - Signature verification (webhook & checkout)
# - Idempotent processing
# - Database persistence
# - Status transitions
# - Email storage
```

**Test coverage**:
- ✅ Valid/invalid signatures
- ✅ Timing-safe comparison
- ✅ Duplicate webhook handling
- ✅ Status transitions (created → paid → failed)
- ✅ Customer email optional/required
- ✅ Real webhook payloads (payment.captured, payment.failed)

## Production Checklist

- [ ] Configure Razorpay dashboard:
  - [ ] API keys generated
  - [ ] Webhook endpoint set
  - [ ] Webhook secret copied
  - [ ] Test payment processed
- [ ] Environment variables set:
  - [ ] RAZORPAY_KEY_ID
  - [ ] RAZORPAY_KEY_SECRET
  - [ ] RAZORPAY_WEBHOOK_SECRET
- [ ] Database migration applied:
  - [ ] `customer_email` column created
  - [ ] Indices created (gateway_ref uniqueness)
- [ ] Frontend component deployed:
  - [ ] RazorpayCheckout component available
  - [ ] Checkout.js SDK loads correctly
  - [ ] Error messages display properly
- [ ] API routes verified:
  - [ ] /api/blackboxops/razorpay-order returns valid order
  - [ ] /api/blackboxops/razorpay-verify validates signatures
  - [ ] /api/blackboxops/razorpay-webhook processes webhooks
- [ ] Monitoring configured:
  - [ ] Webhook success/failure logged
  - [ ] Payment status queries working
  - [ ] Revenue dashboard reflects payments

## Real-World Example

```typescript
// Example: Sell BlackboxOps Starter for ₹299

import { RazorpayCheckout } from "@/components/RazorpayCheckout";
import { Card, CardBody } from "@/components/ui";

export default function BuyStarterPage() {
  return (
    <Card>
      <CardBody>
        <h1>BlackboxOps Starter Edition</h1>
        <p>₹299 - Full access to core features</p>
        
        <RazorpayCheckout
          product="blackboxops_os_starter"
          amount={299}
          onPaymentSuccess={(response) => {
            // Record that this email has paid
            // Send activation email
            // Redirect to dashboard
            window.location.href = "/dashboard";
          }}
          onPaymentFailure={(error) => {
            // Log error for debugging
            console.error(error);
          }}
        />
      </CardBody>
    </Card>
  );
}
```

## Known Limitations & Future Work

1. **Currency**: Only INR supported (easily extensible to USD, EUR, etc.)
2. **Refunds**: Not yet implemented (requires `--refund-razorpay-order` CLI command)
3. **Recurring**: No auto-billing (Subscriptions API exists but not wired to UI)
4. **Email delivery**: Confirmation emails not yet sent (integrate with Resend or SendGrid)
5. **Dispute handling**: No chargeback/dispute workflow

## Files Changed/Created

**Modified**:
- `orchestrator/db.py` - Added `customer_email` column migration
- `orchestrator/cli.py` - Added `--customer-email` argument
- `dashboard/app/api/blackboxops/razorpay-order/route.ts` - Accept customer info
- `dashboard/app/api/blackboxops/razorpay-webhook/route.ts` - Pass webhook ID
- `dashboard/app/api/blackboxops/razorpay-verify/route.ts` - Fixed env var passing

**Created**:
- `dashboard/components/RazorpayCheckout.tsx` - Complete checkout component
- `tests/test_razorpay_checkout_flow.py` - 17 integration tests (100% passing)

## Support & Troubleshooting

**Webhook not triggering**:
- Verify Razorpay dashboard has correct webhook URL
- Check logs for signature verification failures
- Razorpay test mode vs. production keys

**Orders created but not updating status**:
- Check RAZORPAY_WEBHOOK_SECRET is configured
- Verify webhook signature in error response
- May be missing x-razorpay-signature header

**Payment signature failing**:
- Ensure --razorpay-key-secret is passed correctly
- Verify it matches the API Key Secret (not Webhook Secret)
- Check order_id and payment_id are correct

## References

- Razorpay Orders API: https://razorpay.com/docs/api/orders
- Razorpay Checkout: https://razorpay.com/docs/payments/checkout
- Razorpay Webhooks: https://razorpay.com/docs/webhooks/
- HMAC-SHA256: https://tools.ietf.org/html/rfc2104
