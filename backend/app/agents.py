from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .qa_runner import run_playwright_tests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = PROJECT_ROOT / "tests"


@dataclass
class AgentContext:
    user_input: str
    user_story: str = ""
    requirements: list[str] = field(default_factory=list)
    developer_notes: list[str] = field(default_factory=list)
    qa_notes: list[str] = field(default_factory=list)
    architecture_notes: list[str] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)
    deployment_notes: list[str] = field(default_factory=list)


def product_manager_agent(context: AgentContext) -> None:
    context.user_story = (
        "As a new user, I want to register and log in securely "
        "so that I can access my account."
    )


def business_analyst_agent(context: AgentContext) -> None:
    context.requirements = [
        "User can register with name, email, and password.",
        "User can log in with email and password.",
        "Password is stored as a hash, not plain text.",
        "Successful login returns an access token.",
        "Logged-in user can call /api/auth/me.",
    ]


def developer_agent(context: AgentContext) -> None:
    context.developer_notes = [
        "Backend uses FastAPI routes for register, login, and current user.",
        "SQLite stores user records.",
        "Frontend calls the backend with fetch.",
    ]


def qa_agent(context: AgentContext, run_tests: bool = False) -> None:
    context.qa_notes = [
        "Generated test case: user registration.",
        "Generated test case: valid login.",
        "Generated test case: invalid login.",
        "Generated test case: logout functionality.",
        "Automated check: Playwright test file is tests/e2e/login.spec.js.",
    ]

    if not run_tests:
        context.qa_notes.append("Automated test execution skipped. Use --run-tests to run Playwright.")
        return

    print_agent_status("QA Agent - Playwright tests", "STARTED")
    result = run_playwright_tests()
    print(result.output, flush=True)

    if result.passed:
        print_agent_status("QA Agent - Playwright tests", "PASSED")
        context.qa_notes.append(
            f"Playwright tests passed. Tests run: {result.tests_run}. Failures: {result.failures}."
        )
    else:
        print_agent_status("QA Agent - Playwright tests", "FAILED")
        context.qa_notes.append(
            f"Playwright tests failed. Tests run: {result.tests_run}. Failures: {result.failures}."
        )
        context.qa_notes.append("Check the Playwright output above for the exact failure.")


def architect_agent(context: AgentContext) -> None:
    context.architecture_notes = [
        "Current design is good for Phase 1 because frontend and backend are simple.",
        "SQLite is fine for learning; PostgreSQL can be added later.",
        "JWT secret should come from an environment variable in production.",
    ]


def code_review_agent(context: AgentContext) -> None:
    context.review_notes = [
        "Code is split into auth, database, schemas, and main API files.",
        "Password hashing is implemented with bcrypt.",
        "Next improvement: add backend unit tests for API routes.",
    ]


def devops_agent(context: AgentContext) -> None:
    context.deployment_notes = [
        "Local deployment command: python run_server.py",
        "Health check URL: http://127.0.0.1:8000/health",
        "Future deployment can use Docker or Render.",
    ]


def print_agent_status(agent_name: str, status: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {agent_name}: {status}", flush=True)


def run_agent(agent_name: str, action, context: AgentContext, *args) -> None:
    print_agent_status(agent_name, "STARTED")
    action(context, *args)
    print_agent_status(agent_name, "FINISHED")


def run_workflow(user_input: str, run_tests: bool = False) -> AgentContext:
    context = AgentContext(user_input=user_input)

    run_agent("Product Manager Agent", product_manager_agent, context)
    run_agent("Business Analyst Agent", business_analyst_agent, context)
    run_agent("Developer Agent", developer_agent, context)
    run_agent("QA Agent", qa_agent, context, run_tests)
    run_agent("Architect Agent", architect_agent, context)
    run_agent("Code Review Agent", code_review_agent, context)
    run_agent("DevOps Agent", devops_agent, context)

    return context
