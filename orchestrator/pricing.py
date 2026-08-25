"""
Pricing / usage gating -- per-email free-tier tracking + subscription
checks. email is the only identity concept anywhere in this project for
a paying customer -- there's no login system, no account/session model.
That's a real, honest limitation: a customer with two email addresses
gets two free tiers, and there's no way to prevent that without adding
real authentication, which wasn't asked for here and would be a much
bigger feature than pricing gates.

PRODUCT_PRICING is data, not scattered conditionals -- same "agents are
config" philosophy used everywhere else in this project. peopledesk has
no product to attach this to yet (deferred, see PROJECT_STATUS.md) --
its pricing config exists so it's ready the moment the product does,
not because it's wired to anything today.
"""
from datetime import datetime, timedelta

from . import db

PRODUCT_PRICING = {
    # Real pricing decision, 2026-08-24 -- founder saw both products
    # showing "join waitlist" on the real dhansetuhub.in site and set
    # real prices for both. PDF Studio is real and live here
    # (dashboard/app/pdf-studio); PeopleDesk still has no product built
    # behind it (see module docstring) -- this is a pricing decision
    # only, not a claim the product exists.
    "pdf_studio": {"free_uses": 10, "price_inr": 99, "period_days": 365, "label": "Dhansetu PDF Studio — Annual"},
    "peopledesk": {"free_uses": 0, "price_inr": 99, "period_days": 30, "label": "Dhansetu PeopleDesk — Monthly"},
    # Illustrative only -- the founder hasn't set real blackboxOps_OS pricing
    # yet. Present these on the staging Pricing page clearly marked as
    # proposed, not confirmed; don't let a placeholder number pass as a
    # real decision.
    "blackboxops_os_starter": {"free_uses": 0, "price_inr": 2999, "period_days": 30, "label": "blackboxOps_OS Starter — Monthly (proposed)"},
    "blackboxops_os_growth": {"free_uses": 0, "price_inr": 7999, "period_days": 30, "label": "blackboxOps_OS Growth — Monthly (proposed)"},
}


class PricingError(RuntimeError):
    pass


def _validate_product(product: str):
    if product not in PRODUCT_PRICING:
        raise PricingError(f"unknown product '{product}' — expected one of {list(PRODUCT_PRICING)}")


def check_access(email: str, product: str) -> dict:
    """The gate a product's API route calls before doing real work.
    Real, deterministic logic: an active (unexpired) subscription always
    grants access; otherwise access is granted only while free uses
    remain."""
    _validate_product(product)
    pricing = PRODUCT_PRICING[product]

    with db.get_conn() as conn:
        subscription = db.get_active_subscription(conn, email, product)
        if subscription:
            return {"allowed": True, "reason": "active subscription", "requires_payment": False,
                     "remaining_free": None, "subscription": subscription}

        usage = db.get_usage(conn, email, product)
        used = usage["use_count"] if usage else 0
        remaining = max(0, pricing["free_uses"] - used)

        if remaining > 0:
            return {"allowed": True, "reason": f"{remaining} free use(s) remaining", "requires_payment": False,
                     "remaining_free": remaining, "subscription": None}

        return {"allowed": False, "reason": "free tier exhausted, no active subscription", "requires_payment": True,
                 "remaining_free": 0, "subscription": None, "price_inr": pricing["price_inr"], "label": pricing["label"]}


def record_usage(email: str, product: str) -> int:
    """Call only after check_access() allowed the request -- this doesn't
    re-check access, it just increments the counter."""
    _validate_product(product)
    with db.get_conn() as conn:
        return db.increment_usage(conn, email, product)


def create_subscription_payment(email: str, product: str, gateway: str, **gateway_credentials) -> dict:
    """gateway: 'razorpay' or 'payu'. gateway_credentials are passed
    straight through to payment_gateway_manager -- never stored, same
    manual-entry-only rule as every other payment integration here."""
    _validate_product(product)
    pricing = PRODUCT_PRICING[product]
    from . import payment_gateway_manager as pgm

    if gateway == "razorpay":
        result = pgm.create_razorpay_payment_link(
            gateway_credentials["razorpay_key_id"], gateway_credentials["razorpay_key_secret"],
            pricing["price_inr"], pricing["label"], customer_contact=gateway_credentials.get("customer_contact"),
            reference_id=f"{product}:{email}",
        )
        gateway_ref, checkout_url = result["id"], result["short_url"]
    elif gateway == "payu":
        result = pgm.create_payu_checkout(
            gateway_credentials["payu_merchant_key"], gateway_credentials["payu_merchant_salt"],
            pricing["price_inr"], pricing["label"], email, gateway_credentials.get("firstname", "Customer"),
            gateway_credentials.get("phone", ""), gateway_credentials["success_url"], gateway_credentials["failure_url"],
            test_mode=gateway_credentials.get("test_mode", True),
        )
        gateway_ref, checkout_url = result["txnid"], result  # PayU has no single URL -- caller renders result["fields"] as a form
    else:
        raise PricingError(f"unknown gateway '{gateway}' — expected 'razorpay' or 'payu'")

    with db.get_conn() as conn:
        subscription_id = db.insert_subscription(conn, email, product, pricing["price_inr"], gateway, gateway_ref=gateway_ref)

    return {"subscription_id": subscription_id, "gateway": gateway, "gateway_ref": gateway_ref, "checkout": checkout_url}


def confirm_subscription_paid(subscription_id: int) -> dict:
    """Call after verifying the gateway confirms payment (Razorpay:
    --check-payment; PayU: verify_payu_response_hash on the callback).
    Not automatic -- payment confirmation is a real, separate step this
    function doesn't perform itself."""
    valid_until = (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
    with db.get_conn() as conn:
        db.activate_subscription(conn, subscription_id, valid_until)
    return {"subscription_id": subscription_id, "status": "active", "valid_until": valid_until}
