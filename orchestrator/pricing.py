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
    "smartbudget_pro": {"free_uses": 0, "price_inr": 149, "period_days": None, "is_one_time": True, "label": "SmartBudget Pro — One-time"},
    "dhansetu_all_access": {"free_uses": 0, "price_inr": 399, "period_days": None, "is_one_time": True, "label": "DhanSetu All Access — One-time"},
    # Real pricing decision, 2026-08-24 -- founder saw both products
    # showing "join waitlist" on the real dhansetuhub.in site and set
    # real prices for both. PDF Studio is real and live here
    # (dashboard/app/pdf-studio); PeopleDesk still has no product built
    # behind it (see module docstring) -- this is a pricing decision
    # only, not a claim the product exists.
    "pdf_studio": {"free_uses": 10, "price_inr": 99, "period_days": 365, "label": "Dhansetu PDF Studio — Annual"},
    "peopledesk": {"free_uses": 0, "price_inr": 99, "period_days": 30, "label": "Dhansetu PeopleDesk — Monthly"},
    # Real founder decision, 2026-09-09: founding-customer launch pricing,
    # explicitly a discount from the earlier confirmed ₹6,999/₹17,999
    # (2026-08-24) while there's no track record/case studies yet -- not
    # a permanent bargain-bin position. These numbers happen to match
    # what was sitting here marked "(proposed)" from an even earlier,
    # never-finalized round -- coincidence, not a prior decision being
    # silently reused; confirmed fresh tonight against the founder's own
    # explicit instruction, not inherited from the stale placeholder.
    #
    # Changed to ONE-TIME, capped at the first 300 customers, same
    # session (founder: "make it one time for first 300 customers" --
    # then "it showing subscription base, make it one time" when the
    # page copy still read monthly). is_one_time=True means
    # confirm_subscription_paid() sets valid_until=NULL (never expires)
    # instead of the usual +365 days; max_customers is a hard cap
    # enforced in create_subscription_payment() below, counting only
    # 'active' (paid) rows -- an abandoned/pending checkout never
    # occupies a slot a 301st real customer could have used.
    "blackboxops_os_starter": {"free_uses": 0, "price_inr": 2999, "period_days": None, "is_one_time": True, "max_customers": 300, "label": "blackboxOps_OS Starter — One-time (first 300 founding customers)"},
    "blackboxops_os_growth": {"free_uses": 0, "price_inr": 7999, "period_days": None, "is_one_time": True, "max_customers": 300, "label": "blackboxOps_OS Growth — One-time (first 300 founding customers)"},
}


class PricingError(RuntimeError):
    pass


def _validate_product(product: str):
    if product not in PRODUCT_PRICING:
        raise PricingError(f"unknown product '{product}' — expected one of {list(PRODUCT_PRICING)}")


def resolve_order_product(product: str) -> dict:
    """Return the server-owned catalog values used to create a payment order."""
    _validate_product(product)
    item = PRODUCT_PRICING[product]
    return {"product": product, **item,
            "amount_paise": int(round(item["price_inr"] * 100))}


def reconcile_order_payment(order_id: str, status: str, payment_id: str | None = None) -> dict:
    """Apply a verified gateway state exactly once to the entitlement ledger."""
    if status not in {"paid", "failed", "refunded", "chargeback"}:
        raise PricingError(f"unsupported payment status '{status}'")
    with db.get_conn() as conn:
        transaction = db.get_payment_transaction(conn, order_id)
        if transaction is None:
            raise PricingError(f"no payment transaction found for order '{order_id}'")
        current = transaction["status"]
        if status == "failed" and current in {"paid", "refunded", "chargeback"}:
            return {"outcome": "ignored_stale_failure", "transaction_status": current}
        product = transaction["description"]
        _validate_product(product)
        email = (transaction.get("customer_contact") or "").strip().lower()
        if status == "paid" and ("@" not in email or email.startswith("@") or email.endswith("@")):
            raise PricingError("verified payment has no valid customer email; entitlement not granted")
        if status == "paid" and payment_id:
            db.set_payment_transaction_paid(conn, order_id, payment_id)
        else:
            db.update_payment_transaction_status(conn, order_id, status)
        subscription = db.get_subscription_by_gateway_ref(conn, "razorpay", order_id)
        if status == "paid":
            if subscription is None:
                subscription_id = db.insert_subscription(conn, email, product, transaction["amount"], "razorpay", gateway_ref=order_id)
                expiry = None if PRODUCT_PRICING[product].get("is_one_time") else (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
                db.activate_subscription(conn, subscription_id, expiry)
                subscription = db.get_subscription(conn, subscription_id)
            elif subscription["status"] != "active":
                expiry = None if PRODUCT_PRICING[product].get("is_one_time") else (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
                db.activate_subscription(conn, subscription["id"], expiry)
            return {"outcome": "entitlement_active", "entitlement_status": "active", "subscription_id": subscription["id"]}
        if status in {"refunded", "chargeback"}:
            db.cancel_subscription_by_gateway_ref(conn, "razorpay", order_id)
            return {"outcome": "entitlement_revoked", "entitlement_status": "cancelled", "subscription_id": subscription["id"] if subscription else None}
        return {"outcome": "transaction_updated", "transaction_status": status, "subscription_id": subscription["id"] if subscription else None}


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

    max_customers = pricing.get("max_customers")
    if max_customers is not None:
        with db.get_conn() as conn:
            already_sold = db.count_active_subscriptions(conn, product)
        if already_sold >= max_customers:
            raise PricingError(
                f"'{pricing['label']}' is sold out -- all {max_customers} spots at this price are taken "
                f"({already_sold} confirmed). Not creating a payment for a spot that no longer exists."
            )

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
    function doesn't perform itself.

    Real bug fixed 2026-09-10 (Task 15 audit): this used to set a 365-day
    valid_until unconditionally, for every product -- including
    blackboxops_os_starter/growth, which PRODUCT_PRICING already marks
    is_one_time=True and whose label explicitly promises "One-time"
    lifetime access. A customer who paid for that would have had real
    access silently expire in a year despite never being told that would
    happen. db.get_active_subscription() was already written to treat
    valid_until IS NULL as "never expires" -- the write side just never
    used it. Now it does."""
    with db.get_conn() as conn:
        subscription = db.get_subscription(conn, subscription_id)
        if subscription is None:
            raise PricingError(f"no subscription found with id {subscription_id}")
        pricing = PRODUCT_PRICING[subscription["product"]]

        valid_until = None if pricing.get("is_one_time") else (
            datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        db.activate_subscription(conn, subscription_id, valid_until)
    return {"subscription_id": subscription_id, "status": "active", "valid_until": valid_until}
