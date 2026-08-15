from app.llm import interpret_work_request


def test_gemini_interpretation(monkeypatch):
    class FakeResponse:
        text = """
        {
            "title": "Client Follow-up",
            "summary": "Prepare a thank-you email and create a reminder.",
            "priority": "medium",
            "deadline": "next Friday",
            "action_items": [
                {
                    "description": "Prepare a thank-you email",
                    "automatable": true,
                    "route": "EXECUTE_AUTOMATICALLY",
                    "reason": "System can draft email"
                },
                {
                    "description": "Create a reminder for next Friday",
                    "automatable": true,
                    "route": "EXECUTE_AUTOMATICALLY",
                    "reason": "System can set reminder"
                }
            ],
            "missing_information": [],
            "requires_human_confirmation": []
        }
        """

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(
        "app.llm.client",
        FakeClient()
    )

    result = interpret_work_request(
        "Prepare a thank-you email for the client and remind me next Friday."
    )

    assert result.title == "Client Follow-up"
    assert result.priority == "medium"
    assert len(result.action_items) == 2