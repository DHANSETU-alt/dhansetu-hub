"""
Phase 2 Acceptance Gate Orchestrator
Master orchestrator that runs all acceptance gates and generates final report
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from .security_gates import run_security_gates
from .performance_gates import run_performance_gates
from .error_gates import run_error_handling_gates
from .coverage_gates import run_coverage_gates
from .docs_gates import run_documentation_gates


class AcceptanceGateOrchestrator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {}
        self.timestamp = datetime.utcnow().isoformat()

    def run_all_gates(self) -> Dict:
        """Run all acceptance gates"""
        print("=" * 80)
        print("PHASE 2 ACCEPTANCE GATE VERIFICATION")
        print("=" * 80)
        print(f"Timestamp: {self.timestamp}")
        print()

        gates = [
            ("Security Gates", run_security_gates),
            ("Performance Gates", run_performance_gates),
            ("Error Handling Gates", run_error_handling_gates),
            ("Test Coverage Gates", run_coverage_gates),
            ("Documentation Gates", run_documentation_gates),
        ]

        for gate_name, gate_func in gates:
            print(f"Running {gate_name}...")
            try:
                result = gate_func()
                self.results[gate_name] = result
                status = "PASS" if result["status"] == "PASS" else "FAIL"
                print(f"  {status}: {result['passed']}/{result['total_gates']} gates passed")
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                self.results[gate_name] = {
                    "status": "ERROR",
                    "error": str(e),
                    "total_gates": 0,
                    "passed": 0,
                    "failed": 0,
                    "results": []
                }
            print()

        return self._generate_summary()

    def _generate_summary(self) -> Dict:
        """Generate overall summary"""
        total_gates = sum(r.get("total_gates", 0) for r in self.results.values())
        total_passed = sum(r.get("passed", 0) for r in self.results.values())
        total_failed = sum(r.get("failed", 0) for r in self.results.values())

        gate_summaries = {}
        blockers = []

        for gate_name, gate_result in self.results.items():
            status = gate_result.get("status", "ERROR")
            gate_summaries[gate_name] = {
                "status": status,
                "passed": gate_result.get("passed", 0),
                "total": gate_result.get("total_gates", 0),
            }

            if status == "FAIL":
                blockers.append(gate_name)

        overall_status = "APPROVED" if total_failed == 0 and total_gates > 0 else "BLOCKED"

        summary = {
            "timestamp": self.timestamp,
            "overall_status": overall_status,
            "total_gates_run": total_gates,
            "gates_passed": total_passed,
            "gates_failed": total_failed,
            "gate_summaries": gate_summaries,
            "blockers": blockers,
            "detailed_results": self.results,
        }

        return summary

    def write_report(self, output_file: str = None) -> str:
        """Write acceptance report to file"""
        if output_file is None:
            output_file = str(self.project_root / "PHASE2_ACCEPTANCE_REPORT.md")

        report_lines = [
            "# Phase 2 Acceptance Gate Report",
            "",
            f"**Generated:** {self.timestamp}",
            "",
            "## Executive Summary",
            "",
        ]

        # Overall status
        overall_status = "APPROVED" if self.results else "UNKNOWN"
        status_icon = "✅" if overall_status == "APPROVED" else "❌"

        total_gates = sum(r.get("total_gates", 0) for r in self.results.values())
        total_passed = sum(r.get("passed", 0) for r in self.results.values())
        total_failed = sum(r.get("failed", 0) for r in self.results.values())

        if total_gates > 0:
            overall_status = "APPROVED" if total_failed == 0 else "BLOCKED"
            status_icon = "✅" if overall_status == "APPROVED" else "❌"

        report_lines.extend([
            f"{status_icon} **Overall Status: {overall_status}**",
            "",
            f"- Total Gates Run: {total_gates}",
            f"- Gates Passed: {total_passed}",
            f"- Gates Failed: {total_failed}",
            f"- Pass Rate: {(total_passed / total_gates * 100) if total_gates > 0 else 0:.1f}%",
            "",
        ])

        # Blockers
        blockers = [name for name, result in self.results.items() if result.get("status") == "FAIL"]
        if blockers:
            report_lines.extend([
                "### Blockers",
                "",
            ])
            for blocker in blockers:
                report_lines.append(f"- **{blocker}** - See details below")
            report_lines.append("")

        # Recommendations
        report_lines.extend([
            "## Recommendations",
            "",
        ])

        if overall_status == "APPROVED":
            report_lines.extend([
                "✅ **APPROVED FOR PRODUCTION**",
                "",
                "All acceptance gates have passed. The system meets production readiness standards.",
                "",
                "**Next Steps:**",
                "1. Deploy to production environment",
                "2. Monitor error logs and performance metrics",
                "3. Execute post-deployment verification",
                "",
            ])
        else:
            report_lines.extend([
                "❌ **BLOCKED - NEEDS WORK**",
                "",
                "The following gate categories have failures that must be resolved before production deployment:",
                "",
            ])
            for blocker in blockers:
                report_lines.append(f"- {blocker}")
            report_lines.extend([
                "",
                "**Required Actions:**",
                "1. Review failed gates (see details below)",
                "2. Fix identified issues",
                "3. Re-run acceptance gates",
                "4. Obtain approval before deployment",
                "",
            ])

        # Detailed results by gate category
        report_lines.extend([
            "## Detailed Gate Results",
            "",
        ])

        for gate_name, gate_result in self.results.items():
            status = gate_result.get("status", "ERROR")
            status_icon = "✅" if status == "PASS" else "❌"
            passed = gate_result.get("passed", 0)
            total = gate_result.get("total_gates", 0)

            report_lines.extend([
                f"### {gate_name}",
                "",
                f"{status_icon} **Status: {status}**",
                "",
                f"- Passed: {passed}/{total}",
                "",
            ])

            # Individual gate results
            individual_results = gate_result.get("results", [])
            if individual_results:
                report_lines.append("#### Individual Gates")
                report_lines.append("")
                for individual in individual_results:
                    gate_status = "✅" if individual["status"] == "PASS" else "❌"
                    report_lines.append(f"**{individual['name']}** {gate_status}")

                    if individual.get("details"):
                        report_lines.append(f"- {individual['details']}")

                    if individual.get("findings"):
                        for finding in individual["findings"]:
                            report_lines.append(f"- ⚠️ {finding}")

                    if individual.get("metrics"):
                        for metric_key, metric_value in individual["metrics"].items():
                            report_lines.append(f"- {metric_key}: {metric_value}")

                    report_lines.append("")

            report_lines.append("")

        # Deployment checklist
        report_lines.extend([
            "## Deployment Readiness Checklist",
            "",
            "Before production deployment, verify the following:",
            "",
            "- [ ] All security gates PASS",
            "- [ ] All performance gates PASS",
            "- [ ] All error handling gates PASS",
            "- [ ] Code coverage meets minimum (70%)",
            "- [ ] All critical tests passing",
            "- [ ] Documentation is complete and current",
            "- [ ] Secrets are in environment variables (not in code)",
            "- [ ] Database migrations tested",
            "- [ ] Rollback procedure tested",
            "- [ ] Health check endpoint verified",
            "- [ ] Monitoring and alerting configured",
            "- [ ] Backup and recovery procedures tested",
            "- [ ] Post-deployment runbook prepared",
            "",
        ])

        # Final sign-off
        report_lines.extend([
            "## Sign-Off",
            "",
            f"Report Generated: {self.timestamp}",
            "",
            "This report serves as the official Phase 2 acceptance gate verification.",
            "",
            "**Quality Assurance:** Pending human review",
            "",
            "**Deployment Authorization:** Pending stakeholder approval",
            "",
        ])

        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, 'w') as f:
            f.write(report_content)

        print(f"Report written to: {output_file}")
        return output_file


def run_acceptance_gates_full() -> Dict:
    """Run all acceptance gates and generate report"""
    orchestrator = AcceptanceGateOrchestrator()
    summary = orchestrator.run_all_gates()
    orchestrator.write_report()

    # Also write the JSON summary
    json_file = orchestrator.project_root / "PHASE2_ACCEPTANCE_GATE_RESULTS.json"
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nJSON results written to: {json_file}")

    return summary


if __name__ == "__main__":
    result = run_acceptance_gates_full()

    # Print summary
    print("\n" + "=" * 80)
    print("OVERALL RESULT")
    print("=" * 80)
    print(f"Status: {result['overall_status']}")
    print(f"Gates Passed: {result['gates_passed']}/{result['total_gates_run']}")
    if result['blockers']:
        print(f"Blockers: {', '.join(result['blockers'])}")
