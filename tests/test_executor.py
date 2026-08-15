from app.executor import execute_action, execute_actions
from app.schemas import ActionItem, ActionRoute


def test_automatable_action():
    action = ActionItem(
        description="Create a reminder",
        automatable=True,
        route=ActionRoute.EXECUTE_AUTOMATICALLY,
        reason="The system can create a simulated reminder automatically.",
    )

    result = execute_action(action)

    assert result["status"] == "COMPLETED"


def test_non_automatable_action():
    action = ActionItem(
        description="Approve the final report",
        automatable=False,
        route=ActionRoute.PREPARE_FOR_HUMAN_REVIEW,
        reason="A human must approve the final report.",
    )

    result = execute_action(action)

    assert result["status"] == "AWAITING_CONFIRMATION"


def test_execute_multiple_actions():
    actions = [
        ActionItem(
            description="Create a reminder",
            automatable=True,
            route=ActionRoute.EXECUTE_AUTOMATICALLY,
            reason="The system can create a simulated reminder.",
        ),
        ActionItem(
            description="Approve the report",
            automatable=False,
            route=ActionRoute.PREPARE_FOR_HUMAN_REVIEW,
            reason="Human approval is required.",
        ),
    ]

    results = execute_actions(actions)

    assert len(results) == 2
    assert results[0]["status"] == "COMPLETED"
    assert results[1]["status"] == "AWAITING_CONFIRMATION"