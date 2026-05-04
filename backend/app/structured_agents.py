from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .agent_logger import LOG_FILE, write_agent_log
from .qa_runner import run_playwright_tests


WorkflowData = dict[str, Any]
FieldRules = dict[str, type | tuple[type, ...]]


def validate_required_fields(payload: dict[str, Any], rules: FieldRules) -> list[str]:
    errors: list[str] = []
    for field_name, expected_type in rules.items():
        if field_name not in payload:
            errors.append(f"Missing output field: {field_name}")
            continue
        if not isinstance(payload[field_name], expected_type):
            errors.append(
                f"Output field {field_name} must be {format_expected_type(expected_type)}."
            )
    return errors


def format_expected_type(expected_type: type | tuple[type, ...]) -> str:
    if isinstance(expected_type, tuple):
        return " or ".join(item.__name__ for item in expected_type)
    return expected_type.__name__


def require_non_empty_list(payload: dict[str, Any], field_name: str) -> list[str]:
    value = payload.get(field_name)
    if not isinstance(value, list) or not value:
        return [f"Output field {field_name} must be a non-empty list."]
    return []


@dataclass
class AgentResult:
    agent: str
    status: str
    output: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "agent": self.agent,
            "status": self.status,
            "output": self.output,
        }
        if self.error:
            result["error"] = self.error
        return result


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        role: str,
        output_key: str,
        required_inputs: list[str] | None = None,
        required_output_fields: FieldRules | None = None,
    ) -> None:
        self.name = name
        self.role = role
        self.output_key = output_key
        self.required_inputs = required_inputs or []
        self.required_output_fields = required_output_fields or {}

    def execute(self, data: WorkflowData) -> AgentResult:
        missing_inputs = [key for key in self.required_inputs if not data.get(key)]
        if missing_inputs:
            return AgentResult(
                agent=self.name,
                status="failed",
                output={},
                error=f"Missing required input(s): {', '.join(missing_inputs)}",
            )

        try:
            output = self.process(data)
        except Exception as exc:
            return AgentResult(
                agent=self.name,
                status="failed",
                output={},
                error=str(exc),
            )

        if not output:
            return AgentResult(
                agent=self.name,
                status="failed",
                output={},
                error="Agent returned empty output.",
            )

        validation_errors = self.validate_output(output, data)
        if validation_errors:
            return AgentResult(
                agent=self.name,
                status="failed",
                output=output,
                error="; ".join(validation_errors),
            )

        data[self.output_key] = output
        return AgentResult(agent=self.name, status="success", output=output)

    @abstractmethod
    def process(self, data: WorkflowData) -> dict[str, Any]:
        pass

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        if output.get("agent_status") == "failed":
            return [output.get("error", "Agent reported failure.")]
        return validate_required_fields(output, self.required_output_fields)


class ProductManagerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Product Manager",
            role="Format user input into a structured user story.",
            output_key="user_story",
            required_inputs=["user_input"],
            required_output_fields={
                "feature_name": str,
                "original_request": str,
                "story": str,
                "persona": str,
                "business_value": str,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        user_input = data["user_input"].strip()
        feature_name = "User Login System"
        if "register" in user_input.lower() or "registration" in user_input.lower():
            feature_name = "User Registration and Login"

        return {
            "feature_name": feature_name,
            "original_request": user_input,
            "story": "As a user, I want to register and log in so that I can securely access my account.",
            "persona": "Application user",
            "business_value": "Users can create accounts and return later with secure access.",
            "agent_status": "success",
        }

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        errors = super().validate_output(output, data)
        if output.get("original_request") != data.get("user_input", "").strip():
            errors.append("Product Manager output must preserve the original request.")
        return errors


class BusinessAnalystAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Business Analyst",
            role="Add acceptance criteria and validation rules.",
            output_key="requirements",
            required_inputs=["user_story"],
            required_output_fields={
                "functional_requirements": list,
                "acceptance_criteria": list,
                "validation_rules": list,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        return {
            "functional_requirements": [
                "User can register with name, email, and password.",
                "User can log in with email and password.",
                "System stores only hashed passwords.",
                "System returns a token after successful login.",
                "User can log out from the frontend.",
            ],
            "acceptance_criteria": [
                "Registration succeeds when all fields are valid.",
                "Login succeeds with valid credentials.",
                "Login fails with invalid credentials.",
                "Logout clears the displayed user profile.",
            ],
            "validation_rules": [
                "Name must not be empty.",
                "Email must be a valid email address.",
                "Password must be at least 8 characters.",
                "Duplicate email registration must be rejected.",
            ],
            "agent_status": "success",
        }

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        errors = super().validate_output(output, data)
        for field_name in [
            "functional_requirements",
            "acceptance_criteria",
            "validation_rules",
        ]:
            errors.extend(require_non_empty_list(output, field_name))
        return errors


class DeveloperAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Developer",
            role="Simulate code generation with structured implementation output.",
            output_key="developer_output",
            required_inputs=["requirements"],
            required_output_fields={
                "simulated_files": list,
                "api_endpoints": list,
                "implementation_notes": list,
                "completed_requirements": list,
                "not_real_code": bool,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        return {
            "simulated_files": [
                "backend/app/main.py",
                "backend/app/auth.py",
                "backend/app/database.py",
                "frontend/app.js",
            ],
            "api_endpoints": [
                "POST /api/auth/register",
                "POST /api/auth/login",
                "GET /api/auth/me",
            ],
            "implementation_notes": [
                "Use FastAPI for API routes.",
                "Use SQLite for local persistence.",
                "Use bcrypt hashing for passwords.",
                "Use JWT token for authenticated requests.",
            ],
            "completed_requirements": data["requirements"]["functional_requirements"],
            "not_real_code": True,
            "agent_status": "success",
        }

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        errors = super().validate_output(output, data)
        requirements = data["requirements"]["functional_requirements"]
        completed = output.get("completed_requirements", [])
        missing = [item for item in requirements if item not in completed]
        if missing:
            errors.append(
                "Developer output does not cover requirement(s): " + "; ".join(missing)
            )
        return errors


class QAAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="QA",
            role="Map requirements to test cases and optionally run Playwright.",
            output_key="qa_output",
            required_inputs=["requirements", "developer_output"],
            required_output_fields={
                "source": str,
                "requirements_used": list,
                "test_cases": list,
                "coverage": dict,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        requirements = data["requirements"]
        test_cases = [
            {
                "id": "QA-001",
                "requirement": "User can register with name, email, and password.",
                "test": "Create a new user account with valid details.",
                "type": "playwright",
            },
            {
                "id": "QA-002",
                "requirement": "User can log in with email and password.",
                "test": "Log in with valid credentials.",
                "type": "playwright",
            },
            {
                "id": "QA-003",
                "requirement": "Login fails with invalid credentials.",
                "test": "Try logging in with a wrong password and verify the error message.",
                "type": "playwright",
            },
            {
                "id": "QA-004",
                "requirement": "User can log out from the frontend.",
                "test": "Click logout and verify the user profile is cleared.",
                "type": "playwright",
            },
        ]

        output: dict[str, Any] = {
            "source": "requirements",
            "requirements_used": requirements["functional_requirements"],
            "test_cases": test_cases,
            "coverage": {
                "Registration succeeds when all fields are valid.": ["QA-001"],
                "Login succeeds with valid credentials.": ["QA-002"],
                "Login fails with invalid credentials.": ["QA-003"],
                "Logout clears the displayed user profile.": ["QA-004"],
            },
            "agent_status": "success",
        }

        if data.get("run_tests"):
            print("[QA] Playwright tests: STARTED", flush=True)
            test_result = run_playwright_tests()
            print(test_result.output, flush=True)
            output["automation_result"] = test_result.to_dict()
            if not test_result.passed:
                output["agent_status"] = "failed"
                output["error"] = "Automated Playwright tests failed."
            print(f"[QA] Playwright tests: {test_result.qa_status.upper()}", flush=True)

        return output

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        errors = super().validate_output(output, data)
        requirements = data["requirements"]
        if output.get("requirements_used") != requirements["functional_requirements"]:
            errors.append("QA output must use the BA functional requirements.")

        test_ids = [
            test_case.get("id")
            for test_case in output.get("test_cases", [])
            if isinstance(test_case, dict)
        ]
        if len(test_ids) != len(set(test_ids)):
            errors.append("QA test case ids must be unique.")

        coverage = output.get("coverage", {})
        for criterion in requirements["acceptance_criteria"]:
            if not coverage.get(criterion):
                errors.append(f"Missing QA coverage for acceptance criterion: {criterion}")
        return errors


class ArchitectAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Architect",
            role="Check basic system constraints and assumptions.",
            output_key="architecture_review",
            required_inputs=["developer_output"],
            required_output_fields={
                "constraints_checked": list,
                "performance_assumptions": list,
                "risks": list,
                "decision": str,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        return {
            "constraints_checked": [
                "SQLite is acceptable for a beginner local project.",
                "JWT authentication is acceptable for a simple API demo.",
                "Frontend and backend are served from the same FastAPI app.",
            ],
            "performance_assumptions": [
                "Expected users: low traffic learning/demo usage.",
                "Database size: small local SQLite file.",
                "No background workers required yet.",
            ],
            "risks": [
                "Move SECRET_KEY to environment variables before production.",
                "Use PostgreSQL instead of SQLite for multi-user production usage.",
            ],
            "decision": "approved_for_local_demo",
            "agent_status": "success",
        }


class CodeReviewerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="Code Reviewer",
            role="Check dummy best-practice rules.",
            output_key="code_review",
            required_inputs=["developer_output"],
            required_output_fields={
                "rules_checked": list,
                "summary": str,
                "decision": str,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        return {
            "rules_checked": [
                {
                    "rule": "Passwords should not be stored as plain text.",
                    "status": "passed",
                },
                {
                    "rule": "API route names should be clear and REST-like.",
                    "status": "passed",
                },
                {
                    "rule": "Code should be split into small modules.",
                    "status": "passed",
                },
                {
                    "rule": "Production secrets should not be hardcoded.",
                    "status": "warning",
                },
            ],
            "summary": "Code structure is acceptable for a beginner project. Secret handling should improve before production.",
            "decision": "approved_with_warning",
            "agent_status": "success",
        }

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        errors = super().validate_output(output, data)
        failed_rules = [
            item["rule"]
            for item in output.get("rules_checked", [])
            if isinstance(item, dict) and item.get("status") == "failed"
        ]
        if failed_rules:
            errors.append("Code review failed rule(s): " + "; ".join(failed_rules))
        return errors


class DevOpsAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="DevOps",
            role="Simulate deployment steps.",
            output_key="deployment_plan",
            required_inputs=["qa_output", "architecture_review", "code_review"],
            required_output_fields={
                "deployment_steps": list,
                "health_check": str,
                "deployment_status": str,
                "release_gates": dict,
                "pipeline": list,
                "pipeline_status": str,
                "agent_status": str,
            },
        )

    def process(self, data: WorkflowData) -> dict[str, Any]:
        release_gates = {
            "qa": data["qa_output"]["agent_status"],
            "architecture": data["architecture_review"]["decision"],
            "code_review": data["code_review"]["decision"],
        }
        pipeline = self._build_pipeline(data, release_gates)
        pipeline_failed = any(step["status"] == "failure" for step in pipeline)

        return {
            "deployment_steps": [
                "Build application package.",
                "Run validation and QA checks.",
                "Deploy to local demo environment.",
            ],
            "health_check": "GET http://127.0.0.1:8000/health",
            "release_gates": release_gates,
            "pipeline": pipeline,
            "pipeline_status": "failure" if pipeline_failed else "success",
            "deployment_status": (
                "blocked" if pipeline_failed else "deployed_to_local_demo"
            ),
            "agent_status": "failed" if pipeline_failed else "success",
            "error": "Deployment pipeline failed." if pipeline_failed else None,
        }

    def _build_pipeline(
        self, data: WorkflowData, release_gates: dict[str, str]
    ) -> list[dict[str, str]]:
        developer_output = data["developer_output"]
        qa_output = data["qa_output"]
        automation_result = qa_output.get("automation_result")

        build_ok = bool(developer_output.get("simulated_files")) and bool(
            developer_output.get("api_endpoints")
        )
        test_ok = release_gates["qa"] == "success"
        if automation_result:
            test_ok = test_ok and automation_result.get("qa_status") == "passed"
        deploy_ok = (
            build_ok
            and test_ok
            and release_gates["architecture"] == "approved_for_local_demo"
            and release_gates["code_review"].startswith("approved")
        )

        return [
            {
                "name": "Build",
                "status": "success" if build_ok else "failure",
                "message": "Application package created from simulated files.",
            },
            {
                "name": "Test",
                "status": "success" if test_ok else "failure",
                "message": "QA checks passed." if test_ok else "QA checks failed.",
            },
            {
                "name": "Deploy",
                "status": "success" if deploy_ok else "failure",
                "message": (
                    "Local demo deployment completed."
                    if deploy_ok
                    else "Deployment blocked by release gates."
                ),
            },
        ]

    def validate_output(
        self, output: dict[str, Any], data: WorkflowData
    ) -> list[str]:
        errors = super().validate_output(output, data)
        automation = data["qa_output"].get("automation_result")
        if automation and automation.get("qa_status") != "passed":
            errors.append("DevOps cannot deploy because QA automation did not pass.")
        if data["architecture_review"]["decision"] != "approved_for_local_demo":
            errors.append("DevOps cannot deploy without architecture approval.")
        if not data["code_review"]["decision"].startswith("approved"):
            errors.append("DevOps cannot deploy without code review approval.")
        return errors


class WorkflowManager:
    def __init__(self, agents: list[BaseAgent]) -> None:
        self.agents = agents

    def run(self, user_input: str, run_tests: bool = False) -> WorkflowData:
        data: WorkflowData = {
            "user_input": user_input,
            "run_tests": run_tests,
            "execution_log": [],
            "agent_results": [],
            "log_file": str(LOG_FILE),
        }

        if not user_input.strip():
            data["status"] = "failed"
            data["error"] = "User input cannot be empty."
            write_agent_log(
                agent_name="Workflow",
                step="Input validation",
                result="failure",
                details={"error": data["error"]},
            )
            return data

        for agent in self.agents:
            self._log(data, agent.name, "STARTED")
            write_agent_log(
                agent_name=agent.name,
                step="Agent execution started",
                result="started",
                details={"role": agent.role},
            )
            result = agent.execute(data)
            data["agent_results"].append(result.to_dict())

            if result.status != "success":
                self._log(data, agent.name, "FAILED")
                write_agent_log(
                    agent_name=agent.name,
                    step="Agent execution failed",
                    result="failure",
                    details={"error": result.error, "output": result.output},
                )
                data["status"] = "failed"
                data["failed_agent"] = agent.name
                data["error"] = result.error
                data["skipped_agents"] = [
                    skipped_agent.name
                    for skipped_agent in self.agents[self.agents.index(agent) + 1 :]
                ]
                return data

            self._log(data, agent.name, "FINISHED")
            write_agent_log(
                agent_name=agent.name,
                step="Agent execution finished",
                result="success",
                details={"output_key": agent.output_key},
            )

        data["status"] = "finished"
        write_agent_log(
            agent_name="Workflow",
            step="Workflow completed",
            result="success",
            details={"agents_run": len(self.agents)},
        )
        return data

    def _log(self, data: WorkflowData, agent_name: str, status: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {agent_name}: {status}"
        print(message, flush=True)
        data["execution_log"].append(message)


def create_default_workflow_manager() -> WorkflowManager:
    return WorkflowManager(
        agents=[
            ProductManagerAgent(),
            BusinessAnalystAgent(),
            DeveloperAgent(),
            QAAgent(),
            ArchitectAgent(),
            CodeReviewerAgent(),
            DevOpsAgent(),
        ]
    )


def run_structured_workflow(user_input: str, run_tests: bool = False) -> WorkflowData:
    manager = create_default_workflow_manager()
    return manager.run(user_input=user_input, run_tests=run_tests)
