from app.structured_agents import run_structured_workflow
import argparse
import json


def print_value(title: str, value) -> None:
    print()
    print(f"=== {title} ===")
    if isinstance(value, dict):
        print(json.dumps(value, indent=2))
        return
    if isinstance(value, list):
        for item in value:
            print(f"- {item}")
        return
    print(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the structured multi-agent workflow.")
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Ask the QA Agent to trigger Playwright tests.",
    )
    args = parser.parse_args()

    user_input = "Build a secure user registration and login system."

    print("Starting structured multi-agent workflow...")
    result = run_structured_workflow(user_input=user_input, run_tests=args.run_tests)
    print("Structured multi-agent workflow finished.")

    if result["status"] != "finished":
        print_value("Workflow Error", result)
        return

    print_value("User Input", result["user_input"])
    print_value("User Story", result["user_story"])
    print_value("Requirements", result["requirements"])
    print_value("Developer Output", result["developer_output"])
    print_value("QA Output", result["qa_output"])
    print_value("Architecture Review", result["architecture_review"])
    print_value("Code Review", result["code_review"])
    print_value("Deployment Plan", result["deployment_plan"])

    if "automation_result" in result["qa_output"]:
        automation = result["qa_output"]["automation_result"]
        print_value("QA Status", automation["qa_status"])
        print_value("Tests Run", str(automation["tests_run"]))
        print_value("Failures", str(automation["failures"]))


if __name__ == "__main__":
    main()
