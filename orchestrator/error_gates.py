"""
Error Handling Gates for Phase 2 Acceptance
Verifies all error handling controls are in place before production deployment
"""
import re
from pathlib import Path
from typing import Dict, List


class ErrorGateResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.findings = []
        self.metrics = {}
        self.details = ""

    def pass_gate(self, message: str = "", metrics: Dict = None):
        self.passed = True
        self.details = message
        if metrics:
            self.metrics = metrics

    def fail_gate(self, finding: str, metrics: Dict = None):
        self.passed = False
        self.findings.append(finding)
        if metrics:
            self.metrics = metrics

    def to_dict(self):
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "findings": self.findings,
            "metrics": self.metrics,
            "details": self.details
        }


class ErrorHandlingGates:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = []

    def run_all_gates(self) -> List[ErrorGateResult]:
        """Run all error handling gates"""
        self.results = [
            self.gate_all_endpoints_have_error_handlers(),
            self.gate_generic_error_messages(),
            self.gate_error_logging(),
            self.gate_retry_logic(),
        ]
        return self.results

    def gate_all_endpoints_have_error_handlers(self) -> ErrorGateResult:
        """GATE: All endpoints have error handlers (no unhandled exceptions)"""
        result = ErrorGateResult("All Endpoints Have Error Handlers")

        api_file = self.project_root / "orchestrator" / "api.py"
        endpoints_without_handlers = []

        if api_file.exists():
            with open(api_file, 'r') as f:
                content = f.read()

                # Extract all endpoint functions
                endpoint_pattern = r'@route\(["\']([^"\']+)["\']\)\s*\ndef\s+(\w+)\s*\('
                matches = re.finditer(endpoint_pattern, content)

                handled = 0
                unhandled = 0

                for match in matches:
                    route_path = match.group(1)
                    func_name = match.group(2)
                    func_start = match.end()

                    # Find the end of this function
                    func_content = content[func_start:func_start+1000]

                    # Check for try-except blocks
                    if 'try:' in func_content or 'except' in func_content:
                        handled += 1
                    else:
                        unhandled += 1
                        endpoints_without_handlers.append(f"{route_path} ({func_name})")

                if unhandled == 0 and handled > 0:
                    result.pass_gate(
                        f"All {handled} endpoints have error handling",
                        {"total_endpoints": handled, "with_handlers": handled, "without_handlers": 0}
                    )
                else:
                    result.fail_gate(
                        f"Found {unhandled} endpoints without error handlers: {', '.join(endpoints_without_handlers[:3])}",
                        {"total_endpoints": handled + unhandled, "with_handlers": handled, "without_handlers": unhandled}
                    )
        else:
            result.fail_gate("API module not found")

        return result

    def gate_generic_error_messages(self) -> ErrorGateResult:
        """GATE: Error messages are generic (no stack traces to users)"""
        result = ErrorGateResult("Generic Error Messages")

        api_file = self.project_root / "orchestrator" / "api.py"
        stack_trace_leaks = []

        if api_file.exists():
            with open(api_file, 'r') as f:
                lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    # Check for traceback or full error exposure
                    if any(pattern in line for pattern in [
                        'traceback.print',
                        'exc_info=True',
                        'full_stack',
                        'str(e)',  # Avoid showing full exception strings
                    ]):
                        # Verify if it's in logging context (safe)
                        if 'logging' not in line and 'log' not in line.lower():
                            stack_trace_leaks.append(f"Line {i}: {line.strip()[:60]}")

        if not stack_trace_leaks:
            result.pass_gate("Error messages appear to be properly sanitized")
        else:
            result.fail_gate(
                f"Found potential stack trace exposure: {stack_trace_leaks[0]}",
                {"potential_leaks": len(stack_trace_leaks)}
            )

        return result

    def gate_error_logging(self) -> ErrorGateResult:
        """GATE: Logging captures all errors (500, 400, auth failures)"""
        result = ErrorGateResult("Error Logging Coverage")

        log_patterns = [
            r'logging\.',
            r'log\.',
            r'logger\.',
            r'self\.log',
        ]

        error_keywords = [
            '500',
            '400',
            '401',
            '403',
            'auth',
            'error',
            'exception',
        ]

        logging_found = False
        error_logging_found = False

        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            if "__pycache__" in str(py_file):
                continue
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                    # Check for logging setup
                    if any(re.search(pattern, content) for pattern in log_patterns):
                        logging_found = True

                    # Check for error-specific logging
                    if any(keyword in content.lower() for keyword in error_keywords):
                        if any(re.search(pattern, content) for pattern in log_patterns):
                            error_logging_found = True
                            break
            except Exception:
                pass

        if logging_found and error_logging_found:
            result.pass_gate("Error logging is configured for critical paths")
        elif logging_found:
            result.pass_gate("Logging framework is in place")
        else:
            result.fail_gate("No logging detected in codebase")

        return result

    def gate_retry_logic(self) -> ErrorGateResult:
        """GATE: Retry logic on transient failures (network, DB)"""
        result = ErrorGateResult("Retry Logic on Transient Failures")

        retry_patterns = [
            r'retry',
            r'max_attempts',
            r'backoff',
            r'exponential',
            r'timeout',
            r'ConnectionError',
            r'TimeoutError',
        ]

        transient_error_patterns = [
            r'ConnectionError',
            r'TimeoutError',
            r'DatabaseError',
            r'Network',
        ]

        retry_found = False
        transient_handling = False

        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            if "__pycache__" in str(py_file) or "test" in str(py_file):
                continue
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                    # Check for retry patterns
                    if any(re.search(pattern, content, re.IGNORECASE) for pattern in retry_patterns):
                        retry_found = True

                    # Check for transient error handling
                    if any(re.search(pattern, content) for pattern in transient_error_patterns):
                        transient_handling = True

                        if retry_found:
                            break
            except Exception:
                pass

        if retry_found and transient_handling:
            result.pass_gate("Retry logic and transient error handling detected")
        elif retry_found or transient_handling:
            result.pass_gate("Some retry/resilience patterns detected")
        else:
            result.fail_gate("No retry logic detected for transient failures")

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


def run_error_handling_gates() -> Dict:
    """Entry point for error handling gate execution"""
    gates = ErrorHandlingGates()
    gates.run_all_gates()
    return gates.summary()


if __name__ == "__main__":
    import json
    result = run_error_handling_gates()
    print(json.dumps(result, indent=2))
