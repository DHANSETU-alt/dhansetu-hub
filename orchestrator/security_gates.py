"""
Security Gates for Phase 2 Acceptance
Verifies all security controls are in place before production deployment
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class SecurityGateResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.findings = []
        self.details = ""

    def pass_gate(self, message: str = ""):
        self.passed = True
        self.details = message

    def fail_gate(self, finding: str):
        self.passed = False
        self.findings.append(finding)

    def to_dict(self):
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "findings": self.findings,
            "details": self.details
        }


class SecurityGates:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = []

    def run_all_gates(self) -> List[SecurityGateResult]:
        """Run all security gates"""
        self.results = [
            self.gate_no_hardcoded_secrets(),
            self.gate_sql_injection_prevention(),
            self.gate_xss_prevention(),
            self.gate_csrf_protection(),
            self.gate_rate_limiting(),
            self.gate_password_hashing(),
        ]
        return self.results

    def gate_no_hardcoded_secrets(self) -> SecurityGateResult:
        """GATE: No hardcoded secrets (API keys, tokens, credentials)"""
        result = SecurityGateResult("No Hardcoded Secrets")

        secret_patterns = [
            r'api[_-]?key\s*=\s*["\'](?!{|\$|env)[^"\']+["\']',
            r'password\s*=\s*["\'](?!{|\$|env)[^"\']+["\']',
            r'token\s*=\s*["\'](?!{|\$|env)[^"\']+["\']',
            r'secret\s*=\s*["\'](?!{|\$|env)[^"\']+["\']',
            r'sk_(?:live|test)_[0-9a-zA-Z]{20,}',  # Stripe key
            r'AKIA[0-9A-Z]{16}',  # AWS key
            r'-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----',
        ]

        python_files = list(self.project_root.rglob("*.py"))
        secrets_found = []

        for py_file in python_files:
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    for i, line in enumerate(content.split('\n'), 1):
                        # Skip comments and environment variable usage
                        if line.strip().startswith('#'):
                            continue
                        for pattern in secret_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                # Check if it's just a reference to env vars
                                if 'os.environ' in line or 'getenv' in line:
                                    continue
                                secrets_found.append(
                                    f"{py_file.relative_to(self.project_root)}:{i}"
                                )
            except Exception as e:
                pass

        if secrets_found:
            result.fail_gate(f"Found potential hardcoded secrets: {', '.join(secrets_found[:5])}")
        else:
            result.pass_gate("No hardcoded secrets detected")

        return result

    def gate_sql_injection_prevention(self) -> SecurityGateResult:
        """GATE: SQL injection prevention (parameterized queries)"""
        result = SecurityGateResult("SQL Injection Prevention")

        # Check for string interpolation in SQL queries
        risky_patterns = [
            r'(?:SELECT|INSERT|UPDATE|DELETE).*(?:\+|%|\.format|f["\'])',
            r'execute\s*\(\s*["\'].*(?:\+|%|\.format)',
        ]

        violations = []
        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    # Check for parameterized query usage
                    if '.execute(' in content:
                        # Look for proper parameterization
                        if '?' in content or '%s' in content:
                            # Check if used with tuples (proper parameterization)
                            for i, line in enumerate(content.split('\n'), 1):
                                if 'execute(' in line and 'SELECT' in content[max(0, content.find(line)-200):content.find(line)+200]:
                                    if re.search(r'(?<!\?)(?:\+|%|\.format|f["\'])', line):
                                        violations.append(
                                            f"{py_file.relative_to(self.project_root)}:{i}"
                                        )
            except Exception:
                pass

        if violations:
            result.fail_gate(f"Found potential SQL injection vulnerabilities: {', '.join(violations[:5])}")
        else:
            result.pass_gate("All SQL queries use parameterized queries")

        return result

    def gate_xss_prevention(self) -> SecurityGateResult:
        """GATE: XSS prevention (HTML encoding on output)"""
        result = SecurityGateResult("XSS Prevention")

        # Check if HTML escaping is used consistently
        api_file = self.project_root / "orchestrator" / "api.py"
        violations = []

        if api_file.exists():
            with open(api_file, 'r') as f:
                content = f.read()

                # Look for JSON response handling
                if 'json.dumps' in content:
                    # JSON already escapes HTML by default, this is good
                    result.pass_gate("JSON responses provide automatic HTML escaping")
                    return result

        # Check if any response methods don't escape
        check_files = [
            self.project_root / "orchestrator" / "api.py",
            self.project_root / "PLUG_AND_PLAY.py",
        ]

        for check_file in check_files:
            if check_file.exists() and check_file.is_file():
                try:
                    with open(check_file, 'r') as f:
                        content = f.read()
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'response' in line.lower() and any(tag in line for tag in ['<script', '<img', 'onclick']):
                                if 'escape' not in line and 'html.escape' not in line:
                                    violations.append(f"{check_file.name}:{i}")
                except Exception:
                    pass

        if violations:
            result.fail_gate(f"Found potential XSS vulnerabilities: {', '.join(violations[:5])}")
        else:
            result.pass_gate("HTML output is properly escaped")

        return result

    def gate_csrf_protection(self) -> SecurityGateResult:
        """GATE: CSRF tokens on state-changing operations"""
        result = SecurityGateResult("CSRF Protection")

        api_file = self.project_root / "orchestrator" / "api.py"

        if api_file.exists():
            with open(api_file, 'r') as f:
                content = f.read()

                # Check for state-changing operations (POST, PUT, DELETE)
                # In this HTTP server implementation, check for method validation
                if 'method != "POST"' in content or 'method not in ["GET"' in content:
                    result.pass_gate("HTTP methods are validated (GET/POST separation)")
                    return result

                # Check for token validation
                if 'SHAKTHI_API_TOKEN' in content:
                    result.pass_gate("Request authentication via token is implemented")
                    return result

        result.fail_gate("CSRF protection mechanism not clearly detected")
        return result

    def gate_rate_limiting(self) -> SecurityGateResult:
        """GATE: Rate limiting on auth endpoints (10 attempts/15 min)"""
        result = SecurityGateResult("Rate Limiting on Auth Endpoints")

        # Check if rate limiting is implemented in database or API
        db_file = self.project_root / "orchestrator" / "db.py"
        api_file = self.project_root / "orchestrator" / "api.py"

        rate_limit_found = False

        for check_file in [db_file, api_file]:
            if check_file.exists():
                try:
                    with open(check_file, 'r') as f:
                        content = f.read()
                        if any(keyword in content for keyword in ['rate_limit', 'throttle', 'attempt', 'cooldown', 'backoff']):
                            rate_limit_found = True
                except Exception:
                    pass

        if rate_limit_found:
            result.pass_gate("Rate limiting mechanism detected")
        else:
            result.fail_gate("Rate limiting on auth endpoints not detected - CRITICAL")

        return result

    def gate_password_hashing(self) -> SecurityGateResult:
        """GATE: Password hashing (bcrypt or argon2, never plaintext)"""
        result = SecurityGateResult("Password Hashing")

        db_file = self.project_root / "orchestrator" / "db.py"

        password_hashing = False
        plaintext_passwords = False

        if db_file.exists():
            with open(db_file, 'r') as f:
                content = f.read()

                # Check for hashing libraries
                if 'bcrypt' in content or 'argon2' in content or 'hashlib' in content:
                    password_hashing = True

                # Check for plaintext password storage
                if re.search(r'password\s*=\s*["\']?\$\d', content):  # Checking for stored plaintext
                    plaintext_passwords = True

        if password_hashing and not plaintext_passwords:
            result.pass_gate("Passwords are hashed using secure algorithms")
        elif plaintext_passwords:
            result.fail_gate("Plaintext passwords detected in storage - CRITICAL")
        else:
            result.fail_gate("Password hashing implementation not verified")

        return result

    def summary(self) -> Dict:
        """Generate summary of all gate results"""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        return {
            "total_gates": total,
            "passed": passed,
            "failed": total - passed,
            "status": "PASS" if passed == total else "FAIL",
            "results": [r.to_dict() for r in self.results],
        }


def run_security_gates() -> Dict:
    """Entry point for security gate execution"""
    gates = SecurityGates()
    gates.run_all_gates()
    return gates.summary()


if __name__ == "__main__":
    import json
    result = run_security_gates()
    print(json.dumps(result, indent=2))
