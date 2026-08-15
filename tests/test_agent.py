from app.agent import plan_work
from app.schemas import WorkInterpretation, ActionItem, ActionRoute


def test_plan_work(monkeypatch):

    fake_interpretation = WorkInterpretation(
        title="Manager Report",
        summary="Prepare a report for the manager by Friday.",
        priority="medium",
        deadline="Friday",
        action_items=[
            ActionItem(
                description="Prepare a report for the manager",
                automatable=False,
                route=ActionRoute.PREPARE_FOR_HUMAN_REVIEW,
                reason="The report requires human judgment and content creation.",
                tool_name=None,
                tool_params=None,
            )
        ],
        missing_information=[],
        requires_human_confirmation=[]
    )

    def fake_interpret_work_request(user_request):
        return fake_interpretation

    monkeypatch.setattr(
        "app.agent.interpret_work_request",
        fake_interpret_work_request
    )

    result = plan_work(
        "Prepare a report for the manager by Friday"
    )

    assert result is not None
    assert result.title == "Manager Report"
    assert result.summary == "Prepare a report for the manager by Friday."
    assert len(result.action_items) == 1
    assert result.action_items[0].description == "Prepare a report for the manager"