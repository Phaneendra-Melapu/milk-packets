from app.simple_agents import run_basic_agent_workflow


def print_list(title: str, items: list[str]) -> None:
    print()
    print(f"=== {title} ===")
    for item in items:
        print(f"- {item}")


def main() -> None:
    user_input = "I want a simple user registration and login system."

    print("Starting basic multi-agent workflow...")
    result = run_basic_agent_workflow(user_input)

    print()
    print("=== User Input ===")
    print(result["user_input"])

    print()
    print("=== PM Output: User Story ===")
    print(result["user_story"])

    print_list("BA Output: Requirements", result["requirements"])
    print_list("Developer Output: Development Plan", result["development_plan"])
    print_list("QA Output: Test Cases", result["test_cases"])


if __name__ == "__main__":
    main()

