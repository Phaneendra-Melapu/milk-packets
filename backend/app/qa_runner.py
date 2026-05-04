import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = PROJECT_ROOT / "tests"


@dataclass
class TestRunResult:
    command: list[str]
    passed: bool
    return_code: int
    tests_run: int
    failures: int
    output: str

    @property
    def qa_status(self) -> str:
        return "passed" if self.passed else "failed"

    def to_dict(self) -> dict:
        return {
            "qa_status": self.qa_status,
            "tests_run": self.tests_run,
            "failures": self.failures,
            "command": self.command,
            "return_code": self.return_code,
            "output": self.output[-4000:],
        }


def run_playwright_tests() -> TestRunResult:
    npm_command = "npm.cmd" if shutil.which("npm.cmd") else "npm"
    command = [npm_command, "run", "test:json", "--silent"]

    result = subprocess.run(
        command,
        cwd=TESTS_DIR,
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout
    if result.stderr:
        output = f"{output}\n{result.stderr}".strip()

    tests_run, failures = parse_playwright_result(output)

    return TestRunResult(
        command=command,
        passed=result.returncode == 0,
        return_code=result.returncode,
        tests_run=tests_run,
        failures=failures,
        output=output,
    )


def parse_playwright_result(output: str) -> tuple[int, int]:
    try:
        report = json.loads(output)
        return count_tests_from_json_report(report)
    except json.JSONDecodeError:
        return count_tests_from_text_output(output)


def count_tests_from_json_report(report: dict) -> tuple[int, int]:
    tests_run = 0
    failures = 0

    def visit_suite(suite: dict) -> None:
        nonlocal tests_run, failures

        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                tests_run += 1
                if test.get("status") not in {"expected", "flaky", "skipped"}:
                    failures += 1

        for child_suite in suite.get("suites", []):
            visit_suite(child_suite)

    for suite in report.get("suites", []):
        visit_suite(suite)

    return tests_run, failures


def count_tests_from_text_output(output: str) -> tuple[int, int]:
    passed_match = re.search(r"(\d+)\s+passed", output)
    failed_match = re.search(r"(\d+)\s+failed", output)

    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    return passed + failed, failed
