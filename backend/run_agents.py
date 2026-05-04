import argparse

from app.agents import run_workflow


def print_section(title: str, items: list[str] | str) -> None:
    print()
    print(f"=== {title} ===")
    if isinstance(items, str):
        print(items)
        return

    for item in items:
        print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the simple multi-agent workflow.")
    parser.add_argument(
        "--input",
        default="Build a user registration and login system.",
        help="Feature request that agents should process.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Ask the QA Agent to run Playwright tests. Keep the backend server running first.",
    )
    args = parser.parse_args()

    print("Starting multi-agent workflow...")
    context = run_workflow(user_input=args.input, run_tests=args.run_tests)
    print("Multi-agent workflow finished.")

    print_section("User Input", context.user_input)
    print_section("User Story", context.user_story)
    print_section("Requirements", context.requirements)
    print_section("Developer Notes", context.developer_notes)
    print_section("QA Notes", context.qa_notes)
    print_section("Architecture Notes", context.architecture_notes)
    print_section("Code Review Notes", context.review_notes)
    print_section("DevOps Notes", context.deployment_notes)


if __name__ == "__main__":
    main()

