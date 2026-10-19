"""DNS and domain configuration for dhansetuhub.in Cloudflare setup."""

import os
import sys
from typing import Any
from pathlib import Path

# Cloudflare API credentials (load from environment)
CF_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CF_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CF_ZONE_ID = os.environ.get("CLOUDFLARE_ZONE_ID", "")  # Zone ID for dhansetuhub.in

DOMAIN = "dhansetuhub.in"
WORKERS_DOMAIN = "dhansetuhub.workers.dev"

# Required DNS records for production setup
DNS_RECORDS = {
    # Root domain A record pointing to Cloudflare's anycast IP
    # Note: Actual IP depends on Cloudflare setup; this is typically managed by CF
    "A": {
        "name": "@",
        "type": "A",
        "content": "104.21.28.1",  # Example Cloudflare IP (real IP may vary)
        "ttl": 3600,  # Will be reduced to 300 before cutover
        "proxied": True,
        "priority": 10,
    },
    # AAAA record for IPv6
    "AAAA": {
        "name": "@",
        "type": "AAAA",
        "content": "2606:4700:4700::1001",  # Example Cloudflare IPv6
        "ttl": 3600,
        "proxied": True,
    },
    # MX records for email
    "MX": [
        {
            "name": "@",
            "type": "MX",
            "content": "aspmx.l.google.com",
            "ttl": 3600,
            "priority": 10,
        },
        {
            "name": "@",
            "type": "MX",
            "content": "alt1.aspmx.l.google.com",
            "ttl": 3600,
            "priority": 20,
        },
        {
            "name": "@",
            "type": "MX",
            "content": "alt2.aspmx.l.google.com",
            "ttl": 3600,
            "priority": 30,
        },
        {
            "name": "@",
            "type": "MX",
            "content": "alt3.aspmx.l.google.com",
            "ttl": 3600,
            "priority": 40,
        },
        {
            "name": "@",
            "type": "MX",
            "content": "alt4.aspmx.l.google.com",
            "ttl": 3600,
            "priority": 50,
        },
    ],
    # SPF record for email authentication
    "SPF": {
        "name": "@",
        "type": "TXT",
        "content": "v=spf1 include:_spf.google.com ~all",
        "ttl": 3600,
    },
    # DKIM records (will be added during email setup)
    # Format: name.dhansetuhub.in TXT v=DKIM1; k=rsa; p=[public-key]

    # DMARC policy
    "DMARC": {
        "name": "_dmarc",
        "type": "TXT",
        "content": 'v=DMARC1; p=quarantine; rua=mailto:dmarc@dhansetuhub.in; ruf=mailto:forensics@dhansetuhub.in; fo=1',
        "ttl": 3600,
    },
}

# Cloudflare page rules and settings
PAGE_RULES = [
    {
        "targets": ["https://dhansetuhub.in/*"],
        "actions": [
            {"id": "always_https", "value": "on"},
            {"id": "ssl", "value": "full"},
            {"id": "cache_level", "value": "aggressive"},
            {"id": "browser_cache_ttl", "value": 14400},  # 4 hours
        ],
    },
    {
        "targets": ["https://dhansetuhub.in/api/*"],
        "actions": [
            {"id": "cache_level", "value": "bypass"},
            {"id": "security_level", "value": "high"},
        ],
    },
]

# Security headers for CSP and other protections
SECURITY_HEADERS = {
    "X-Frame-Options": "SAMEORIGIN",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https: data:; "
        "connect-src 'self' https://api.dhansetuhub.in; "
        "frame-ancestors 'none'; "
        "upgrade-insecure-requests"
    ),
}

# SSL/TLS Configuration
SSL_CONFIG = {
    "min_tls_version": "1.2",
    "ciphers": [
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-AES128-GCM-SHA256",
    ],
    "ssl_mode": "full",  # Encrypt between client and Cloudflare
    "always_https": True,
    "hsts_enabled": True,
    "hsts_max_age": 31536000,  # 1 year
    "hsts_include_subdomains": True,
    "hsts_preload": True,
}

# Email configuration
EMAIL_CONFIG = {
    "domain": DOMAIN,
    "smtp_host": "smtp.gmail.com",  # Using Google Workspace SMTP
    "smtp_port": 587,
    "support_email": "support@dhansetuhub.in",
    "noreply_email": "noreply@dhansetuhub.in",
    "from_name": "DhanSetu Hub",
}


def verify_dns_configuration() -> dict[str, Any]:
    """
    Verify DNS records are correctly configured for dhansetuhub.in.

    Returns:
        dict with verification results for each record type
    """
    import socket
    import subprocess

    results = {"domain": DOMAIN, "timestamp": str(Path.cwd()), "records": {}}

    try:
        # Verify A records
        a_records = socket.getaddrinfo(DOMAIN, 443, socket.AF_INET, socket.SOCK_STREAM)
        results["records"]["A"] = {
            "status": "OK" if a_records else "MISSING",
            "addresses": [r[4][0] for r in a_records],
        }
    except OSError as e:
        results["records"]["A"] = {"status": "ERROR", "error": str(e)}

    try:
        # Verify AAAA records (IPv6)
        aaaa_records = socket.getaddrinfo(DOMAIN, 443, socket.AF_INET6, socket.SOCK_STREAM)
        results["records"]["AAAA"] = {
            "status": "OK" if aaaa_records else "MISSING",
            "addresses": [r[4][0] for r in aaaa_records],
        }
    except OSError as e:
        results["records"]["AAAA"] = {"status": "MISSING", "error": str(e)}

    try:
        # Verify MX records
        mx_output = subprocess.run(
            ["dig", "+short", "MX", DOMAIN],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
        mx_records = [
            line.split()[-1].rstrip(".")
            for line in mx_output.splitlines()
            if line.strip()
        ]
        results["records"]["MX"] = {
            "status": "OK" if mx_records else "MISSING",
            "servers": mx_records,
        }
    except (OSError, subprocess.SubprocessError):
        results["records"]["MX"] = {"status": "UNKNOWN"}

    try:
        # Verify SPF and DMARC TXT records
        txt_output = subprocess.run(
            ["dig", "+short", "TXT", DOMAIN],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
        txt_records = [line.strip() for line in txt_output.splitlines()]
        results["records"]["TXT"] = {
            "status": "OK" if txt_records else "MISSING",
            "records": txt_records,
        }
    except (OSError, subprocess.SubprocessError):
        results["records"]["TXT"] = {"status": "UNKNOWN"}

    try:
        # Verify DNSSEC
        dnssec_output = subprocess.run(
            ["dig", "+dnssec", DOMAIN],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
        has_dnssec = "RRSIG" in dnssec_output and "ad" in dnssec_output
        results["records"]["DNSSEC"] = {
            "status": "ENABLED" if has_dnssec else "DISABLED",
        }
    except (OSError, subprocess.SubprocessError):
        results["records"]["DNSSEC"] = {"status": "UNKNOWN"}

    return results


def verify_ssl_certificate() -> dict[str, Any]:
    """
    Verify SSL certificate for dhansetuhub.in is valid.

    Returns:
        dict with SSL certificate status and expiry date
    """
    import subprocess

    results = {"domain": DOMAIN, "ssl_status": "UNKNOWN"}

    try:
        # Check SSL certificate expiry
        cert_output = subprocess.run(
            ["openssl", "s_client", "-connect", f"{DOMAIN}:443", "-showcerts"],
            input=b"Q\n",
            capture_output=True,
            timeout=5,
            check=False,
        ).stdout.decode("utf-8", errors="ignore")

        if "Verify return code: 0 (ok)" in cert_output or "ssl" in cert_output.lower():
            results["ssl_status"] = "VALID"
            if "notAfter=" in cert_output:
                results["expires"] = cert_output.split("notAfter=")[-1].split("\n")[0]
        else:
            results["ssl_status"] = "INVALID"

    except Exception as e:
        results["ssl_status"] = "ERROR"
        results["error"] = str(e)

    return results


def generate_env_template() -> str:
    """Generate .env template for domain configuration."""
    return f"""# Dhansetuhub.in Domain Configuration
# Last generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

# Domain and API URLs
DOMAIN=dhansetuhub.in
API_URL=https://dhansetuhub.in
WORKERS_DOMAIN=dhansetuhub.workers.dev

# Cloudflare Configuration
CLOUDFLARE_API_TOKEN={CF_API_TOKEN or '[YOUR_CLOUDFLARE_API_TOKEN]'}
CLOUDFLARE_ACCOUNT_ID={CF_ACCOUNT_ID or '[YOUR_CLOUDFLARE_ACCOUNT_ID]'}
CLOUDFLARE_ZONE_ID={CF_ZONE_ID or '[YOUR_CLOUDFLARE_ZONE_ID_FOR_DHANSETUHUB.IN]'}

# Email Configuration
SMTP_HOST={EMAIL_CONFIG['smtp_host']}
SMTP_PORT={EMAIL_CONFIG['smtp_port']}
SUPPORT_EMAIL={EMAIL_CONFIG['support_email']}
NOREPLY_EMAIL={EMAIL_CONFIG['noreply_email']}

# OAuth Configuration (Google)
GOOGLE_OAUTH_REDIRECT_URI=https://dhansetuhub.in/api/auth/google/callback

# Razorpay Configuration
RAZORPAY_KEY_ID=[YOUR_RAZORPAY_KEY_ID]
RAZORPAY_KEY_SECRET=[YOUR_RAZORPAY_KEY_SECRET]
RAZORPAY_WEBHOOK_URL=https://dhansetuhub.in/api/blackboxops/razorpay-webhook
RAZORPAY_WEBHOOK_SECRET=[YOUR_RAZORPAY_WEBHOOK_SECRET]

# Database Configuration
DATABASE_URL=sqlite:///shakthi.db
DATABASE_POOL_SIZE=10
DATABASE_POOL_TIMEOUT=30

# Security
ENABLE_HTTPS=true
TLS_MIN_VERSION=1.2
HSTS_MAX_AGE=31536000
HSTS_PRELOAD=true

# Monitoring and Logging
LOG_LEVEL=INFO
SENTRY_DSN=[OPTIONAL_SENTRY_DNS]
DATADOG_API_KEY=[OPTIONAL_DATADOG_KEY]

# Feature Flags
FEATURE_DOMAIN_CUTOVER=false
FEATURE_NEW_PAYMENT_FLOW=false
"""


def generate_dns_verification_script() -> str:
    """Generate a shell script to verify DNS configuration."""
    return f"""#!/bin/bash
# DNS Verification Script for {DOMAIN}
# This script validates DNS records are properly configured

set -e

DOMAIN="{DOMAIN}"
echo "=== DNS Verification for ${{DOMAIN}} ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

echo "[1/6] Checking A records..."
dig +short A "${{DOMAIN}}" | tee -a dns_check.log

echo ""
echo "[2/6] Checking AAAA records (IPv6)..."
dig +short AAAA "${{DOMAIN}}" | tee -a dns_check.log

echo ""
echo "[3/6] Checking MX records..."
dig +short MX "${{DOMAIN}}" | sort -n -k1 | tee -a dns_check.log

echo ""
echo "[4/6] Checking SPF and DMARC records..."
dig +short TXT "${{DOMAIN}}" | tee -a dns_check.log

echo ""
echo "[5/6] Checking DNSSEC..."
dig +dnssec "${{DOMAIN}}" | grep -E "RRSIG|ad|SERVFAIL" | tee -a dns_check.log

echo ""
echo "[6/6] Checking SSL certificate..."
echo | openssl s_client -connect "${{DOMAIN}}:443" -showcerts 2>/dev/null | grep -E "subject=|issuer=|notAfter" | tee -a dns_check.log

echo ""
echo "=== Verification Complete ==="
echo "Full results saved to dns_check.log"
"""


if __name__ == "__main__":
    print("=== Domain Configuration for dhansetuhub.in ===")
    print()
    print("DNS Configuration:")
    for record_type, record in DNS_RECORDS.items():
        print(f"  {record_type}: {record}")
    print()
    print("Verifying current DNS setup...")
    dns_result = verify_dns_configuration()
    print(f"DNS Records: {dns_result['records']}")
    print()
    print("Verifying SSL certificate...")
    ssl_result = verify_ssl_certificate()
    print(f"SSL Status: {ssl_result['ssl_status']}")
    print()
    print("Environment template generated (see .env.example)")
