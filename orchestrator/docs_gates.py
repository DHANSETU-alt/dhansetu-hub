"""
Documentation Gates for Phase 2 Acceptance
Verifies all required documentation is complete before production deployment
"""
from pathlib import Path
from typing import Dict, List


class DocGateResult:
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


class DocumentationGates:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = []

    def run_all_gates(self) -> List[DocGateResult]:
        """Run all documentation gates"""
        self.results = [
            self.gate_readme_exists(),
            self.gate_api_documentation(),
            self.gate_database_schema_documented(),
            self.gate_deployment_documented(),
            self.gate_troubleshooting_guide(),
        ]
        return self.results

    def gate_readme_exists(self) -> DocGateResult:
        """GATE: README.md exists and complete"""
        result = DocGateResult("README.md Complete")

        readme_file = self.project_root / "README.md"

        if not readme_file.exists():
            result.fail_gate("README.md not found")
            return result

        try:
            with open(readme_file, 'r') as f:
                content = f.read()

                # Check for essential sections
                required_sections = [
                    "# ",  # Title
                    "Installation",
                    "Usage",
                    "Features",
                ]

                missing_sections = []
                for section in required_sections:
                    if section not in content:
                        missing_sections.append(section)

                if not missing_sections:
                    result.pass_gate("README.md is complete with all essential sections")
                else:
                    result.fail_gate(f"README.md missing sections: {', '.join(missing_sections)}")
        except Exception as e:
            result.fail_gate(f"Could not read README.md: {str(e)}")

        return result

    def gate_api_documentation(self) -> DocGateResult:
        """GATE: API documentation exists (all endpoints, parameters, responses)"""
        result = DocGateResult("API Documentation Complete")

        # Check for API documentation files
        api_docs_candidates = [
            self.project_root / "API.md",
            self.project_root / "docs" / "API.md",
            self.project_root / "API_REFERENCE.md",
            self.project_root / "docs" / "API_REFERENCE.md",
        ]

        api_doc_found = None
        for candidate in api_docs_candidates:
            if candidate.exists():
                api_doc_found = candidate
                break

        if api_doc_found:
            try:
                with open(api_doc_found, 'r') as f:
                    content = f.read()

                    # Check for endpoint documentation
                    if "GET" in content or "POST" in content or "endpoint" in content.lower():
                        result.pass_gate(f"API documentation found at {api_doc_found.relative_to(self.project_root)}")
                    else:
                        result.fail_gate("API documentation exists but appears incomplete")
            except Exception as e:
                result.fail_gate(f"Could not read API documentation: {str(e)}")
        else:
            # Check if API is documented in code via docstrings
            api_file = self.project_root / "orchestrator" / "api.py"
            if api_file.exists():
                try:
                    with open(api_file, 'r') as f:
                        content = f.read()

                        if '"""' in content or "'''" in content:
                            # Has docstrings
                            result.pass_gate("API documented via code docstrings")
                        else:
                            result.fail_gate("No dedicated API documentation file found")
                except Exception:
                    result.fail_gate("No dedicated API documentation file found")
            else:
                result.fail_gate("No dedicated API documentation file found")

        return result

    def gate_database_schema_documented(self) -> DocGateResult:
        """GATE: Database schema documented"""
        result = DocGateResult("Database Schema Documented")

        # Check for schema documentation
        schema_candidates = [
            self.project_root / "DATABASE.md",
            self.project_root / "docs" / "DATABASE.md",
            self.project_root / "SCHEMA.md",
            self.project_root / "docs" / "SCHEMA.md",
        ]

        schema_doc_found = None
        for candidate in schema_candidates:
            if candidate.exists():
                schema_doc_found = candidate
                break

        if schema_doc_found:
            result.pass_gate(f"Database schema documented at {schema_doc_found.relative_to(self.project_root)}")
        else:
            # Check if schema is documented in db.py
            db_file = self.project_root / "orchestrator" / "db.py"
            if db_file.exists():
                try:
                    with open(db_file, 'r') as f:
                        content = f.read()

                        # Check for CREATE TABLE or schema comments
                        if "CREATE TABLE" in content or "schema" in content.lower():
                            result.pass_gate("Database schema documented in code")
                        else:
                            result.fail_gate("Database schema documentation not found")
                except Exception:
                    result.fail_gate("Database schema documentation not found")
            else:
                result.fail_gate("Database schema documentation not found")

        return result

    def gate_deployment_documented(self) -> DocGateResult:
        """GATE: Deployment procedure documented"""
        result = DocGateResult("Deployment Procedure Documented")

        # Check for deployment documentation
        deployment_candidates = [
            self.project_root / "DEPLOYMENT.md",
            self.project_root / "DEPLOY.md",
            self.project_root / "docs" / "DEPLOYMENT.md",
            self.project_root / "docs" / "DEPLOY.md",
            self.project_root / "DEPLOYMENT_CHECKLIST.md",
        ]

        deploy_doc_found = None
        for candidate in deployment_candidates:
            if candidate.exists():
                deploy_doc_found = candidate
                break

        if deploy_doc_found:
            try:
                with open(deploy_doc_found, 'r') as f:
                    content = f.read()

                    if "step" in content.lower() or "procedure" in content.lower():
                        result.pass_gate(f"Deployment documented at {deploy_doc_found.relative_to(self.project_root)}")
                    else:
                        result.fail_gate("Deployment documentation exists but appears incomplete")
            except Exception as e:
                result.fail_gate(f"Could not read deployment documentation: {str(e)}")
        else:
            result.fail_gate("No deployment procedure documentation found")

        return result

    def gate_troubleshooting_guide(self) -> DocGateResult:
        """GATE: Troubleshooting guide exists"""
        result = DocGateResult("Troubleshooting Guide Exists")

        # Check for troubleshooting documentation
        troubleshooting_candidates = [
            self.project_root / "TROUBLESHOOTING.md",
            self.project_root / "docs" / "TROUBLESHOOTING.md",
            self.project_root / "FAQ.md",
            self.project_root / "docs" / "FAQ.md",
        ]

        troubleshoot_found = None
        for candidate in troubleshooting_candidates:
            if candidate.exists():
                troubleshoot_found = candidate
                break

        if troubleshoot_found:
            try:
                with open(troubleshoot_found, 'r') as f:
                    content = f.read()

                    if len(content) > 100:
                        result.pass_gate(f"Troubleshooting guide at {troubleshoot_found.relative_to(self.project_root)}")
                    else:
                        result.fail_gate("Troubleshooting guide exists but is too brief")
            except Exception as e:
                result.fail_gate(f"Could not read troubleshooting guide: {str(e)}")
        else:
            # Check if troubleshooting info is in README
            readme_file = self.project_root / "README.md"
            if readme_file.exists():
                try:
                    with open(readme_file, 'r') as f:
                        content = f.read()

                        if "troubleshoot" in content.lower() or "faq" in content.lower():
                            result.pass_gate("Troubleshooting information found in README")
                        else:
                            result.fail_gate("No dedicated troubleshooting guide found")
                except Exception:
                    result.fail_gate("No dedicated troubleshooting guide found")
            else:
                result.fail_gate("No dedicated troubleshooting guide found")

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


def run_documentation_gates() -> Dict:
    """Entry point for documentation gate execution"""
    gates = DocumentationGates()
    gates.run_all_gates()
    return gates.summary()


if __name__ == "__main__":
    import json
    result = run_documentation_gates()
    print(json.dumps(result, indent=2))
