from app.schemas import WorkInterpretation


def create_execution_plan(
    interpretation: WorkInterpretation
) -> list:
    """
    Convert the Gemini work interpretation into
    a list of executable actions.
    """

    execution_plan = []

    for action in interpretation.action_items:

        execution_plan.append({
            "description": action.description,
            "automatable": action.automatable,
            "route": action.route.value,
            "requires_confirmation": (
                action.route.value == "PREPARE_FOR_HUMAN_REVIEW"
            ),
            "tool_name": action.tool_name,
            "tool_params": (
                action.tool_params.model_dump()
                if action.tool_params
                else None
            )
        })

    return execution_plan