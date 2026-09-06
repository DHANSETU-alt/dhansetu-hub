"""
Razorpay Payment Links -- Offer A ("Website Health Audit") payment
collection. stdlib urllib only, same pattern as telegram.py -- one HTTP
API, no reason to add the `razorpay` SDK as a dependency for it.

Key ID / Key Secret are ALWAYS passed in explicitly by the caller, NEVER
read from a stored config file or env var fallback -- unlike Telegram/
Sheets, there isn't even an env var convenience path here, because this
is money movement, not alerting. Manual entry, every invocation, same
founder requirement as Telegram/Sheets credentials but held to a
stricter standard given what's at stake.

No webhook receiver -- this system is localhost-only by design (see
README "Security gaps"), so payment status is checked on demand via the
Payment Links fetch API (a pull), never pushed to us. Run
`--check-payment` after sending a link to see if it's been paid.

NOT verified against a live Razorpay account -- no API keys were
available when this was built. The request/response shapes below are
real, documented Razorpay Payment Links API v1 calls; treat the first
real `--create-payment-link` as the verification step, same as this
project's Telegram and Sheets integrations were.
"""
import base64
import json
import urllib.error
import urllib.request

API_BASE = "https://api.razorpay.com/v1/payment_links"


class RazorpayError(RuntimeError):
    pass


def _auth_header(key_id: str, key_secret: str) -> str:
    if not key_id or not key_secret:
        raise RazorpayError("Razorpay key_id and key_secret are both required")
    token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
    return f"Basic {token}"


def _call(method: str, url: str, key_id: str, key_secret: str, body: dict = None, timeout: int = 15) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": _auth_header(key_id, key_secret),
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore")
        raise RazorpayError(f"Razorpay API error {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RazorpayError(f"could not reach Razorpay API: {e}") from e


def create_payment_link(key_id: str, key_secret: str, amount_inr: float, description: str,
                         customer_name: str = None, customer_contact: str = None,
                         customer_email: str = None, reference_id: str = None) -> dict:
    """amount_inr is rupees (e.g. 999.0) -- Razorpay's API wants paise
    (integer, amount_inr * 100), converted here so every caller works in
    the same units the rest of this project's finance code uses."""
    if amount_inr <= 0:
        raise RazorpayError(f"amount_inr must be positive, got {amount_inr}")

    body = {
        "amount": round(amount_inr * 100),
        "currency": "INR",
        "description": description,
        "reminder_enable": True,
        "notify": {"sms": bool(customer_contact), "email": bool(customer_email)},
    }
    if reference_id:
        body["reference_id"] = reference_id
    if customer_name or customer_contact or customer_email:
        customer = {}
        if customer_name:
            customer["name"] = customer_name
        if customer_contact:
            customer["contact"] = customer_contact
        if customer_email:
            customer["email"] = customer_email
        body["customer"] = customer

    result = _call("POST", API_BASE, key_id, key_secret, body=body)
    return {
        "id": result["id"], "short_url": result["short_url"], "status": result["status"],
        "amount_inr": result["amount"] / 100, "raw": result,
    }


def get_payment_link_status(key_id: str, key_secret: str, payment_link_id: str) -> dict:
    result = _call("GET", f"{API_BASE}/{payment_link_id}", key_id, key_secret)
    return {"id": result["id"], "status": result["status"], "amount_inr": result["amount"] / 100,
            "amount_paid_inr": result.get("amount_paid", 0) / 100, "raw": result}
