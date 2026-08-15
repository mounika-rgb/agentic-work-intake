from app.llm import interpret_work_request
from app.schemas import WorkInterpretation


def plan_work(user_request: str) -> WorkInterpretation:
    """
    Interpret a user's work request and return a structured work plan.
    """

    interpretation = interpret_work_request(user_request)

    return interpretation