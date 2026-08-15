from app.planner import create_execution_plan
from app.schemas import WorkInterpretation, ActionItem, ActionRoute


def test_create_execution_plan():

    interpretation = WorkInterpretation(
        title="Client Follow-up",
        summary="Prepare a thank-you email.",
        priority="medium",
        deadline="next Friday",
        action_items=[
            ActionItem(
                description="Prepare a thank-you email",
                automatable=True,
                route=ActionRoute.EXECUTE_AUTOMATICALLY,
                reason="System can draft emails automatically"
            ),
            ActionItem(
                description="Send the email to the client",
                automatable=False,
                route=ActionRoute.PREPARE_FOR_HUMAN_REVIEW,
                reason="Requires human approval to send"
            )
        ],
        missing_information=[],
        requires_human_confirmation=[]
    )

    plan = create_execution_plan(interpretation)

    assert len(plan) == 2

    assert plan[0]["description"] == "Prepare a thank-you email"
    assert plan[0]["automatable"] is True
    assert plan[0]["requires_confirmation"] is False

    assert plan[1]["automatable"] is False
    assert plan[1]["requires_confirmation"] is True