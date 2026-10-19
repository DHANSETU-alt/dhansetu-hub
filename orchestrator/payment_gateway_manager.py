"""
Payment Gateway Manager -- Razorpay Payment Links (wraps payments.py,
doesn't duplicate it), Razorpay Subscriptions (new), Stripe Checkout
(new), and UPI deep links (new, zero-dependency, no gateway account
needed at all).

Same rule as payments.py throughout: every credential is passed in by
the caller, every invocation, NEVER stored to disk or read from an env
var fallback. This is money movement -- held to the strictest version of
this project's "manual entry only" standard.

NOT verified against live Stripe or Razorpay Subscriptions accounts --
no API keys were available when this was built. Request/response shapes
are real, documented API calls (Stripe Checkout Sessions API, Razorpay
Subscriptions API v1); treat the first real call as the verification
step, same as every other integration in this project.
"""
import hashlib
import hmac
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid

from . import payments as razorpay_links  # Razorpay Payment Links -- reused, not duplicated

RAZORPAY_SUBSCRIPTIONS_BASE = "https://api.razorpay.com/v1"
STRIPE_BASE = "https://api.stripe.com/v1"
PAYU_TEST_URL = "https://test.payu.in/_payment"
PAYU_PRODUCTION_URL = "https://secure.payu.in/_payment"


class PaymentGatewayError(RuntimeError):
    pass


# --- Razorpay Payment Links (thin re-export) --------------------------------

def create_razorpay_payment_link(key_id: str, key_secret: str, amount_inr: float, description: str, **kwargs) -> dict:
    try:
        return razorpay_links.create_payment_link(key_id, key_secret, amount_inr, description, **kwargs)
    except razorpay_links.RazorpayError as e:
        raise PaymentGatewayError(str(e)) from e


# --- Razorpay Subscriptions ---------------------------------------------

def create_razorpay_subscription_plan(key_id: str, key_secret: str, amount_inr: float, plan_name: str,
                                       interval: int = 1, period: str = "monthly") -> dict:
    """period: daily | weekly | monthly | yearly (Razorpay's own vocabulary)."""
    body = {
        "period": period, "interval": interval,
        "item": {"name": plan_name, "amount": round(amount_inr * 100), "currency": "INR"},
    }
    result = razorpay_links._call("POST", f"{RAZORPAY_SUBSCRIPTIONS_BASE}/plans", key_id, key_secret, body=body)
    return {"plan_id": result["id"], "raw": result}


def create_razorpay_subscription(key_id: str, key_secret: str, plan_id: str, total_count: int = 12,
                                  customer_notify: bool = True) -> dict:
    body = {"plan_id": plan_id, "total_count": total_count, "customer_notify": 1 if customer_notify else 0}
    result = razorpay_links._call("POST", f"{RAZORPAY_SUBSCRIPTIONS_BASE}/subscriptions", key_id, key_secret, body=body)
    return {"subscription_id": result["id"], "short_url": result.get("short_url"), "status": result["status"], "raw": result}


# --- Stripe Checkout ------------------------------------------------------

def _stripe_call(secret_key: str, path: str, form_body: dict) -> dict:
    """Stripe's REST API is form-urlencoded with bracket notation for
    nested params (e.g. line_items[0][price_data][unit_amount]), not
    JSON -- a real, documented quirk of their API, not a mistake here."""
    import base64
    import json as _json

    data = urllib.parse.urlencode(form_body).encode()
    token = base64.b64encode(f"{secret_key}:".encode()).decode()
    req = urllib.request.Request(f"{STRIPE_BASE}{path}", data=data, method="POST", headers={
        "Authorization": f"Basic {token}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return _json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise PaymentGatewayError(f"Stripe API error {e.code}: {e.read().decode(errors='ignore')}") from e
    except urllib.error.URLError as e:
        raise PaymentGatewayError(f"could not reach Stripe API: {e}") from e


def create_stripe_checkout_session(secret_key: str, amount: float, currency: str, description: str,
                                    success_url: str, cancel_url: str) -> dict:
    if not secret_key:
        raise PaymentGatewayError("Stripe secret_key is required")
    if amount <= 0:
        raise PaymentGatewayError(f"amount must be positive, got {amount}")
    body = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price_data][currency]": currency.lower(),
        "line_items[0][price_data][unit_amount]": round(amount * 100),
        "line_items[0][price_data][product_data][name]": description,
        "line_items[0][quantity]": 1,
    }
    result = _stripe_call(secret_key, "/checkout/sessions", body)
    return {"session_id": result["id"], "checkout_url": result["url"], "raw": result}


def check_stripe_session_status(secret_key: str, session_id: str) -> dict:
    import base64
    import json as _json

    token = base64.b64encode(f"{secret_key}:".encode()).decode()
    req = urllib.request.Request(f"{STRIPE_BASE}/checkout/sessions/{session_id}",
                                  headers={"Authorization": f"Basic {token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = _json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise PaymentGatewayError(f"Stripe API error {e.code}: {e.read().decode(errors='ignore')}") from e
    return {"session_id": result["id"], "payment_status": result["payment_status"],
            "amount_total": (result.get("amount_total") or 0) / 100}


def check_razorpay_subscription_status(key_id: str, key_secret: str, subscription_id: str) -> dict:
    result = razorpay_links._call("GET", f"{RAZORPAY_SUBSCRIPTIONS_BASE}/subscriptions/{subscription_id}", key_id, key_secret)
    return {"subscription_id": result["id"], "status": result["status"]}


# --- Razorpay Orders + Checkout.js -- a real fixed-price, on-page checkout,
# NOT a Payment Link. The founder's own real, repeated complaint about the
# Payment Links flow above: it hands the customer a URL to open separately
# (or the founder a link to paste/share) instead of a "Pay Now" button that
# takes their card/UPI right on the page. This is the standard Razorpay
# pattern for that: the server creates an Order for an exact amount, the
# browser opens Razorpay's own Checkout modal against that order_id (via
# checkout.js, loaded client-side -- not built here, that's the frontend's
# job), and the resulting payment is tied to that one order, one amount,
# no separate link ever generated or shared. NOT verified against a live
# Razorpay account -- same honest caveat as every other gateway function in
# this file; the Orders API and the checkout signature formula below are
# both Razorpay's own documented v1 behavior.
def create_razorpay_order(key_id: str, key_secret: str, amount_inr: float, receipt: str,
                           notes: dict = None) -> dict:
    if amount_inr <= 0:
        raise PaymentGatewayError(f"amount_inr must be positive, got {amount_inr}")
    body = {
        "amount": int(round(amount_inr * 100)),  # Razorpay amounts are in paise, always an integer
        "currency": "INR",
        "receipt": receipt,
        "notes": notes or {},
    }
    try:
        result = razorpay_links._call("POST", f"{RAZORPAY_SUBSCRIPTIONS_BASE}/orders", key_id, key_secret, body=body)
    except razorpay_links.RazorpayError as e:
        # Same real bug this project already fixed once for the Payment
        # Links path (create_razorpay_payment_link above): _call() raises
        # payments.RazorpayError, not this module's PaymentGatewayError --
        # left uncaught, that's a raw traceback (file paths included)
        # leaking straight into an API response instead of a clean error.
        # Confirmed live: a bad test key here produced exactly that until
        # this except was added.
        raise PaymentGatewayError(str(e)) from e
    return {"order_id": result["id"], "amount": result["amount"], "currency": result["currency"], "raw": result}


def verify_razorpay_webhook_signature(raw_body: bytes, signature: str, webhook_secret: str) -> bool:
    """Real gap this project's own comments flagged and left open (see
    payments.py's module docstring: 'No webhook receiver -- this system
    is localhost-only by design... payment status is checked on demand').
    A webhook is the SERVER-TO-SERVER confirmation that a payment
    actually completed -- distinct from verify_razorpay_checkout_signature
    above, which only covers the customer's browser telling us checkout
    finished (real, but a browser can go offline/crash before that call
    lands; the webhook is Razorpay's own authoritative, retried-until-
    acked notification). Razorpay's documented formula: HMAC-SHA256 of
    the RAW request body (not a re-serialized/re-parsed version -- even a
    single whitespace difference breaks the signature) using a separate
    Webhook Secret configured in the Razorpay dashboard, never the same
    value as the API Key Secret."""
    expected = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_razorpay_checkout_signature(key_secret: str, order_id: str, payment_id: str, signature: str) -> bool:
    """Real security requirement, not optional: Checkout.js's success
    callback runs entirely in the customer's browser, so it must never be
    trusted on its own -- a tampered client could claim success for an
    unpaid order. Razorpay's own documented formula: HMAC-SHA256 of
    "order_id|payment_id" using the merchant's key_secret must match the
    signature Razorpay's server actually sent back."""
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(key_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# --- PayU (India) -- hash-signed form POST, not a REST API ----------------
#
# PayU's checkout isn't a JSON API call like Razorpay/Stripe -- the
# merchant builds a hash-signed HTML form and the customer's browser
# POSTs it directly to PayU's checkout URL. What this returns is that
# form's field values + action URL; the caller (a web page) renders an
# auto-submitting form with them. NOT verified against a live PayU
# merchant account -- no test credentials were available when this was
# built. The hash formula below is PayU's own documented sequence;
# treat the first real checkout attempt (in PayU's test/sandbox mode,
# test.payu.in) as the verification step, same as every other
# integration in this project.

def _payu_hash(key: str, txnid: str, amount: str, productinfo: str, firstname: str, email: str, salt: str,
               udf1: str = "", udf2: str = "", udf3: str = "", udf4: str = "", udf5: str = "") -> str:
    """PayU's documented v1 hash sequence -- built as a list-join rather
    than a hand-typed pipe-delimited string, since miscounting the 5
    trailing empty fields (udf6-udf10) by even one pipe silently produces
    a hash PayU will reject with no useful error."""
    fields = [key, txnid, amount, productinfo, firstname, email, udf1, udf2, udf3, udf4, udf5, "", "", "", "", "", salt]
    return hashlib.sha512("|".join(fields).encode()).hexdigest()


def create_payu_checkout(merchant_key: str, merchant_salt: str, amount_inr: float, product_info: str,
                          email: str, firstname: str, phone: str, success_url: str, failure_url: str,
                          test_mode: bool = True) -> dict:
    if not (merchant_key and merchant_salt):
        raise PaymentGatewayError("PayU merchant_key and merchant_salt are both required")
    if amount_inr <= 0:
        raise PaymentGatewayError(f"amount_inr must be positive, got {amount_inr}")

    txnid = uuid.uuid4().hex[:20]
    amount_str = f"{amount_inr:.2f}"
    txn_hash = _payu_hash(merchant_key, txnid, amount_str, product_info, firstname, email, merchant_salt)

    return {
        "action_url": PAYU_TEST_URL if test_mode else PAYU_PRODUCTION_URL,
        "txnid": txnid,
        "fields": {
            "key": merchant_key, "txnid": txnid, "amount": amount_str, "productinfo": product_info,
            "firstname": firstname, "email": email, "phone": phone,
            "surl": success_url, "furl": failure_url, "hash": txn_hash,
        },
    }


def verify_payu_response_hash(merchant_key: str, merchant_salt: str, status: str, txnid: str, amount: str,
                               productinfo: str, firstname: str, email: str, response_hash: str,
                               udf1: str = "", udf2: str = "", udf3: str = "", udf4: str = "", udf5: str = "") -> bool:
    """PayU's REVERSE hash sequence, used to verify a payment-success
    callback actually came from PayU and wasn't forged -- a real security
    requirement for any PayU integration, not optional."""
    fields = [merchant_salt, status, udf5, udf4, udf3, udf2, udf1, email, firstname, productinfo, amount, txnid, merchant_key]
    expected = hashlib.sha512("|".join(fields).encode()).hexdigest()
    return expected == response_hash


# --- UPI deep links (zero dependency, no gateway account needed) -----------

_VPA_PATTERN = re.compile(r"^[\w.\-]{2,256}@[\w.\-]{2,64}$")


def generate_upi_link(vpa: str, payee_name: str, amount_inr: float, note: str = "") -> str:
    """Builds a real upi://pay deep link per the NPCI UPI linking spec --
    any UPI app (GPay, PhonePe, Paytm, BHIM...) can open this directly.
    No API key, no gateway account, no dependency -- works today with
    nothing but a real UPI ID."""
    if not _VPA_PATTERN.match(vpa or ""):
        raise PaymentGatewayError(f"'{vpa}' doesn't look like a valid UPI ID (expected name@bank format)")
    if amount_inr <= 0:
        raise PaymentGatewayError(f"amount_inr must be positive, got {amount_inr}")
    params = {"pa": vpa, "pn": payee_name, "am": f"{amount_inr:.2f}", "cu": "INR"}
    if note:
        params["tn"] = note
    return "upi://pay?" + urllib.parse.urlencode(params)


# --- Gateway status (booleans only, never echoes back a secret) -----------

def gateway_status(razorpay_key_id: str = None, razorpay_key_secret: str = None,
                    stripe_secret_key: str = None, upi_vpa: str = None,
                    payu_merchant_key: str = None, payu_merchant_salt: str = None) -> dict:
    status = {
        "razorpay": {"configured": bool(razorpay_key_id and razorpay_key_secret), "valid": None},
        "stripe": {"configured": bool(stripe_secret_key), "valid": None},
        "upi": {"configured": bool(upi_vpa), "valid": None},
        # PayU has no cheap "ping" endpoint to validate credentials without
        # attempting a real transaction -- configured-only, honestly.
        "payu": {"configured": bool(payu_merchant_key and payu_merchant_salt), "valid": None},
    }
    if status["razorpay"]["configured"]:
        try:
            razorpay_links._call("GET", "https://api.razorpay.com/v1/payments?count=1",
                                  razorpay_key_id, razorpay_key_secret)
            status["razorpay"]["valid"] = True
        except razorpay_links.RazorpayError:
            status["razorpay"]["valid"] = False
    if status["stripe"]["configured"]:
        try:
            _stripe_call(stripe_secret_key, "/balance", {})
            status["stripe"]["valid"] = True
        except PaymentGatewayError:
            status["stripe"]["valid"] = False
    if status["upi"]["configured"]:
        status["upi"]["valid"] = bool(_VPA_PATTERN.match(upi_vpa))
    return status
