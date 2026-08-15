from app.schemas import ActionItem, ActionRoute, WorkInterpretation


def test_work_interpretation():
    data = WorkInterpretation(
        title="Partner Discussion Follow-up",
        summary="Follow up after the partner discussion.",
        priority="medium",
        action_items=[
            ActionItem(
                description="Draft a thank-you email",
                automatable=True,
                route=ActionRoute.PREPARE_FOR_HUMAN_REVIEW,
                reason="The email can be drafted automatically but requires human approval.",
            ),
            ActionItem(
                description="Approve the email before sending",
                automatable=False,
                route=ActionRoute.PREPARE_FOR_HUMAN_REVIEW,
                reason="Approval must be performed by a human.",
            ),
        ],
        missing_information=[],
        requires_human_confirmation=[
            "Email requires human approval"
        ],
    )

    assert data.title == "Partner Discussion Follow-up"
    assert len(data.action_items) == 2
    assert data.action_items[0].route == ActionRoute.PREPARE_FOR_HUMAN_REVIEW