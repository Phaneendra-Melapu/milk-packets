def product_manager_agent(user_input: str) -> str:
    user_story = (
        "As a user, I want to register and log in "
        "so that I can securely access my account."
    )
    return user_story


def business_analyst_agent(user_story: str) -> list[str]:
    requirements = [
        "Create a registration form with name, email, and password.",
        "Create a login form with email and password.",
        "Validate email and password input.",
        "Store passwords securely using hashing.",
        "Show a success message after login.",
    ]
    return requirements


def developer_agent(requirements: list[str]) -> list[str]:
    development_plan = [
        "Build FastAPI register and login API endpoints.",
        "Save user data in SQLite.",
        "Use bcrypt to hash passwords.",
        "Use JWT token for logged-in users.",
        "Connect the frontend form to the backend API.",
    ]
    return development_plan


def qa_agent(development_plan: list[str]) -> list[str]:
    test_cases = [
        "Test user registration with valid details.",
        "Test duplicate email registration.",
        "Test login with correct email and password.",
        "Test login with wrong password.",
        "Test that logged-in user profile is displayed.",
    ]
    return test_cases


def run_basic_agent_workflow(user_input: str) -> dict:
    print("User Input -> Product Manager Agent")
    user_story = product_manager_agent(user_input)

    print("Product Manager Agent -> Business Analyst Agent")
    requirements = business_analyst_agent(user_story)

    print("Business Analyst Agent -> Developer Agent")
    development_plan = developer_agent(requirements)

    print("Developer Agent -> QA Agent")
    test_cases = qa_agent(development_plan)

    print("Basic multi-agent workflow finished.")

    return {
        "user_input": user_input,
        "user_story": user_story,
        "requirements": requirements,
        "development_plan": development_plan,
        "test_cases": test_cases,
    }

