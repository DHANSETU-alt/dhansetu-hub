"""Monitoring setup for dhansetuhub.in domain post-cutover."""

import os
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from pathlib import Path


class DomainMonitor:
    """Monitor domain health, SSL certificates, and DNS resolution."""

    def __init__(self, domain: str = "dhansetuhub.in", check_interval: int = 3600):
        """
        Initialize domain monitor.

        Args:
            domain: Domain to monitor
            check_interval: Seconds between health checks
        """
        self.domain = domain
        self.check_interval = check_interval
        self.metrics = []

    def check_ssl_certificate(self) -> dict[str, Any]:
        """
        Check SSL certificate validity and expiry.

        Returns:
            dict with certificate status
        """
        import subprocess

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": self.domain,
            "check_type": "SSL_CERTIFICATE",
            "status": "UNKNOWN",
            "valid": False,
            "expiry_days": None,
            "issuer": None,
            "subject": None,
        }

        try:
            # Get certificate info
            cmd = f"echo | openssl s_client -connect {self.domain}:443 -showcerts 2>/dev/null"
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

            if proc.returncode == 0:
                output = proc.stdout

                # Extract certificate details
                if "Verify return code: 0 (ok)" in output:
                    result["status"] = "VALID"
                    result["valid"] = True
                elif "Verify return code: 20 (unable to get local issuer certificate)" in output:
                    result["status"] = "VALID_SELF_SIGNED"
                    result["valid"] = True
                else:
                    result["status"] = "INVALID"

                # Extract expiry date
                import re
                expiry_match = re.search(r"notAfter=([^\n]+)", output)
                if expiry_match:
                    expiry_str = expiry_match.group(1)
                    # Parse OpenSSL date format (e.g., "Oct  1 12:00:00 2026 GMT")
                    try:
                        expiry = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z")
                        now = datetime.now(timezone.utc).replace(tzinfo=None)
                        result["expiry_days"] = (expiry - now).days
                    except:
                        result["expiry_days"] = None

                # Extract subject and issuer
                subject_match = re.search(r"subject=([^\n]+)", output)
                if subject_match:
                    result["subject"] = subject_match.group(1)

                issuer_match = re.search(r"issuer=([^\n]+)", output)
                if issuer_match:
                    result["issuer"] = issuer_match.group(1)
            else:
                result["status"] = "ERROR"
                result["error"] = proc.stderr

        except subprocess.TimeoutExpired:
            result["status"] = "TIMEOUT"
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)

        return result

    def check_dns_resolution(self) -> dict[str, Any]:
        """
        Check DNS resolution for domain.

        Returns:
            dict with DNS resolution status
        """
        import socket
        import subprocess

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": self.domain,
            "check_type": "DNS_RESOLUTION",
            "status": "UNKNOWN",
            "a_records": [],
            "aaaa_records": [],
            "mx_records": [],
        }

        try:
            # Check A records
            try:
                a_records = socket.getaddrinfo(self.domain, 80, socket.AF_INET)
                result["a_records"] = list(set(r[4][0] for r in a_records))
            except OSError:
                result["a_records"] = []

            # Check AAAA records
            try:
                aaaa_records = socket.getaddrinfo(self.domain, 80, socket.AF_INET6)
                result["aaaa_records"] = list(set(r[4][0] for r in aaaa_records))
            except OSError:
                result["aaaa_records"] = []

            # Check MX records
            try:
                mx_output = subprocess.run(
                    ["dig", "+short", "MX", self.domain],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                ).stdout
                result["mx_records"] = [
                    line.split()[-1].rstrip(".")
                    for line in mx_output.splitlines()
                    if line.strip()
                ]
            except Exception:
                result["mx_records"] = []

            # Determine status
            if result["a_records"] or result["aaaa_records"]:
                result["status"] = "RESOLVED"
            else:
                result["status"] = "UNRESOLVED"

        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)

        return result

    def check_http_status(self) -> dict[str, Any]:
        """
        Check HTTP/HTTPS status codes.

        Returns:
            dict with HTTP status
        """
        import urllib.request
        import urllib.error

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": self.domain,
            "check_type": "HTTP_STATUS",
            "status": "UNKNOWN",
            "http_code": None,
            "redirect_chain": [],
            "response_time": None,
        }

        try:
            start = time.time()

            # Try HTTPS first
            url = f"https://{self.domain}/"
            try:
                response = urllib.request.urlopen(url, timeout=10)
                result["http_code"] = response.status
                result["status"] = "OK" if response.status == 200 else f"HTTP_{response.status}"
                result["response_time"] = time.time() - start
            except urllib.error.HTTPError as e:
                result["http_code"] = e.code
                result["status"] = f"HTTP_{e.code}"
                result["response_time"] = time.time() - start
            except urllib.error.URLError as e:
                result["status"] = "UNREACHABLE"
                result["error"] = str(e)

        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)

        return result

    def check_redirect_chain(self) -> dict[str, Any]:
        """
        Check redirect chains from workers.dev to dhansetuhub.in.

        Returns:
            dict with redirect chain
        """
        import urllib.request
        import urllib.error

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": self.domain,
            "check_type": "REDIRECT_CHAIN",
            "status": "UNKNOWN",
            "workers_dev_redirects": False,
            "redirect_chain": [],
        }

        try:
            # Check if workers.dev is redirecting to main domain
            workers_url = "https://dhansetuhub.workers.dev/"

            class RedirectHandler(urllib.request.HTTPRedirectHandler):
                def __init__(self):
                    super().__init__()
                    self.redirect_chain = []

                def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                    self.redirect_chain.append({"from": req.get_full_url(), "to": newurl, "code": code})
                    return urllib.request.HTTPRedirectHandler.redirect_request(
                        self, req, fp, code, msg, hdrs, newurl
                    )

            opener = urllib.request.build_opener(RedirectHandler())

            try:
                opener.open(workers_url, timeout=10)
                result["workers_dev_redirects"] = True
                result["redirect_chain"] = opener.handlers[0].redirect_chain if hasattr(opener.handlers[0], 'redirect_chain') else []
                result["status"] = "OK"
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                if hasattr(e, 'code') and e.code in (301, 302, 303, 307, 308):
                    result["workers_dev_redirects"] = True
                    result["status"] = "REDIRECTING"
                else:
                    result["workers_dev_redirects"] = False
                    result["status"] = "NOT_REDIRECTING"

        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)

        return result

    def check_uptime(self) -> dict[str, Any]:
        """
        Check domain uptime (simple ping-like check).

        Returns:
            dict with uptime status
        """
        import urllib.request
        import urllib.error

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": self.domain,
            "check_type": "UPTIME",
            "status": "UNKNOWN",
            "is_up": False,
            "response_time": None,
        }

        try:
            start = time.time()
            url = f"https://{self.domain}/health"

            try:
                response = urllib.request.urlopen(url, timeout=10)
                result["is_up"] = response.status == 200
                result["status"] = "UP" if result["is_up"] else "DEGRADED"
            except urllib.error.HTTPError as e:
                # 404 is OK if the service is up (just no /health endpoint)
                if e.code == 404:
                    result["is_up"] = True
                    result["status"] = "UP"
                else:
                    result["is_up"] = False
                    result["status"] = f"DOWN (HTTP {e.code})"
            except urllib.error.URLError:
                result["is_up"] = False
                result["status"] = "DOWN"

            result["response_time"] = time.time() - start

        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)

        return result

    def run_all_checks(self) -> list[dict[str, Any]]:
        """
        Run all monitoring checks.

        Returns:
            list of check results
        """
        checks = [
            self.check_ssl_certificate(),
            self.check_dns_resolution(),
            self.check_http_status(),
            self.check_redirect_chain(),
            self.check_uptime(),
        ]

        self.metrics.extend(checks)
        return checks

    def generate_health_report(self, output_path: str = "domain_health_report.json"):
        """
        Generate health report from collected metrics.

        Args:
            output_path: Path to save report
        """
        report = {
            "domain": self.domain,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_checks": len(self.metrics),
            "checks": self.metrics,
            "summary": self._summarize_metrics(),
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def _summarize_metrics(self) -> dict[str, Any]:
        """Summarize all collected metrics."""
        summary = {
            "ssl_certificate": {"status": "UNKNOWN", "expiry_days": None},
            "dns_resolution": {"status": "UNKNOWN", "resolved": False},
            "http_status": {"status": "UNKNOWN", "reachable": False},
            "redirect_chain": {"workers_redirecting": False},
            "uptime": {"status": "UNKNOWN", "is_up": False},
            "overall": "UNKNOWN",
        }

        for metric in self.metrics:
            check_type = metric.get("check_type")

            if check_type == "SSL_CERTIFICATE":
                summary["ssl_certificate"]["status"] = metric.get("status")
                summary["ssl_certificate"]["expiry_days"] = metric.get("expiry_days")
            elif check_type == "DNS_RESOLUTION":
                summary["dns_resolution"]["status"] = metric.get("status")
                summary["dns_resolution"]["resolved"] = metric.get("status") == "RESOLVED"
            elif check_type == "HTTP_STATUS":
                summary["http_status"]["status"] = metric.get("status")
                summary["http_status"]["reachable"] = metric.get("status") in ("OK", "HTTP_200")
            elif check_type == "REDIRECT_CHAIN":
                summary["redirect_chain"]["workers_redirecting"] = metric.get("workers_dev_redirects", False)
            elif check_type == "UPTIME":
                summary["uptime"]["status"] = metric.get("status")
                summary["uptime"]["is_up"] = metric.get("is_up", False)

        # Determine overall health
        all_ok = (
            summary["ssl_certificate"]["status"] in ("VALID", "VALID_SELF_SIGNED") and
            summary["dns_resolution"]["resolved"] and
            summary["http_status"]["reachable"] and
            summary["uptime"]["is_up"]
        )

        summary["overall"] = "HEALTHY" if all_ok else "DEGRADED"

        return summary


def create_monitoring_alerts(
    domain: str = "dhansetuhub.in",
    output_path: str = "monitoring_alerts.yaml"
) -> str:
    """
    Generate monitoring alert configuration.

    Args:
        domain: Domain to monitor
        output_path: Path to save alert config

    Returns:
        YAML alert configuration
    """
    alert_config = f"""# Monitoring Alerts for {domain}
# Deploy to your monitoring system (Datadog, New Relic, etc.)

alerts:
  - name: "SSL Certificate Expiry - 30 Days"
    domain: {domain}
    check_type: ssl_certificate
    condition: "expiry_days < 30"
    severity: CRITICAL
    notification_channels:
      - slack
      - email
    runbook: https://docs.dhansetuhub.in/runbooks/ssl-expiry

  - name: "SSL Certificate Expiry - 7 Days"
    domain: {domain}
    check_type: ssl_certificate
    condition: "expiry_days < 7"
    severity: CRITICAL
    notification_channels:
      - slack
      - email
      - pagerduty
    runbook: https://docs.dhansetuhub.in/runbooks/ssl-expiry

  - name: "SSL Certificate Invalid"
    domain: {domain}
    check_type: ssl_certificate
    condition: "status != 'VALID' and status != 'VALID_SELF_SIGNED'"
    severity: CRITICAL
    notification_channels:
      - slack
      - email
      - pagerduty
    runbook: https://docs.dhansetuhub.in/runbooks/ssl-invalid

  - name: "DNS Resolution Failure"
    domain: {domain}
    check_type: dns_resolution
    condition: "status == 'UNRESOLVED'"
    severity: CRITICAL
    notification_channels:
      - slack
      - email
      - pagerduty
    runbook: https://docs.dhansetuhub.in/runbooks/dns-failure

  - name: "Domain Unreachable"
    domain: {domain}
    check_type: http_status
    condition: "status == 'UNREACHABLE'"
    severity: CRITICAL
    notification_channels:
      - slack
      - email
      - pagerduty
    runbook: https://docs.dhansetuhub.in/runbooks/domain-unreachable

  - name: "High HTTP Error Rate"
    domain: {domain}
    check_type: http_status
    condition: "http_code >= 500"
    severity: HIGH
    notification_channels:
      - slack
      - email
    runbook: https://docs.dhansetuhub.in/runbooks/http-errors

  - name: "Domain Down"
    domain: {domain}
    check_type: uptime
    condition: "is_up == false"
    severity: CRITICAL
    notification_channels:
      - slack
      - email
      - pagerduty
    runbook: https://docs.dhansetuhub.in/runbooks/domain-down

  - name: "Slow Response Time"
    domain: {domain}
    check_type: http_status
    condition: "response_time > 2.0"
    severity: MEDIUM
    notification_channels:
      - slack
    runbook: https://docs.dhansetuhub.in/runbooks/slow-response

sla_targets:
  - metric: "uptime"
    target: 99.9
    measurement_window: "monthly"
  - metric: "response_time"
    target: 200  # milliseconds
    percentile: "p95"
  - metric: "error_rate"
    target: 0.1  # 0.1%
    measurement_window: "hourly"

check_schedule:
  - check_type: "ssl_certificate"
    interval: "daily"
  - check_type: "dns_resolution"
    interval: "10_minutes"
  - check_type: "http_status"
    interval: "5_minutes"
  - check_type: "uptime"
    interval: "1_minute"
  - check_type: "redirect_chain"
    interval: "hourly"
"""

    with open(output_path, "w") as f:
        f.write(alert_config)

    return alert_config


if __name__ == "__main__":
    monitor = DomainMonitor("dhansetuhub.in")

    print("=== Running Domain Health Checks ===")
    checks = monitor.run_all_checks()

    for check in checks:
        print(f"\n{check['check_type']}:")
        print(f"  Status: {check['status']}")
        if "error" in check:
            print(f"  Error: {check['error']}")

    print("\n\nGenerating health report...")
    report = monitor.generate_health_report()
    print(f"Report saved to domain_health_report.json")

    print("\nGenerating monitoring alerts...")
    create_monitoring_alerts()
    print("Alerts saved to monitoring_alerts.yaml")
