import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.schemas import WorkInterpretation

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=GEMINI_API_KEY)


def interpret_work_request(user_request: str) -> WorkInterpretation:
    prompt = f"""
You are an AI work-intake assistant.

Analyze the user's work request and convert it into a structured work plan.

You must break the request down into specific Action Items and populate the metadata fields.

For each Action Item, you must determine:
1. `description`: A clear action item statement.
2. `automatable`: Set to true ONLY if the action maps to one of our available tools (listed below) AND is fully concrete.
3. `route`: Select one of:
   - `EXECUTE_AUTOMATICALLY`: Use ONLY for fully concrete automated tasks that do not produce drafts or require human confirmation (e.g. running a website health check, setting a simulated reminder, searching stored work).
   - `PREPARE_FOR_HUMAN_REVIEW`: Use for automatable tasks that generate communication drafts or documents requiring review (e.g. drafting emails, generating markdown briefs).
   - `REQUIRES_CLARIFICATION`: Use if the action is too vague or refers to unspecified files, people, or details (e.g. "send it to everyone", "check the site" without a URL).
   - `CANNOT_EXECUTE`: Use if the task requires tools or capabilities we do not have (e.g. sending real emails, deploying servers, scheduling real Google Calendar invites, scheduling meetings).
4. `reason`: Explain the choice of route.
5. `tool_name`: Set to one of these strings if applicable, or null if none match:
   - 'web_check': For auditing or checking websites. Extract the URL into `tool_params`.
   - 'draft_communication': For drafting emails, messages, or Slack texts. Extract `recipient` and `context` into `tool_params`.
   - 'generate_markdown_brief': For generating brief/summary documents of tasks/work items.
   - 'simulate_reminder': For setting alerts/reminders. Extract `due_date_or_duration` into `tool_params`.
   - 'search_stored_work': For searching previous work records. Extract `query` into `tool_params`.
6. `tool_params`: A key-value dictionary of arguments for the selected tool, or null.

Available Tools:
- 'web_check': args: {{"url": "<extracted_url>"}}
- 'draft_communication': args: {{"recipient": "<recipient_name_or_email>", "context": "<what_to_draft>"}}
- 'generate_markdown_brief': args: {{}}
- 'simulate_reminder': args: {{"due_date_or_duration": "<natural_language_date_or_duration>"}}
- 'search_stored_work': args: {{"query": "<search_keyword>"}}

Rules:
1. If the request is ambiguous or missing important details (e.g., "Please take care of the documentation and send it to everyone before the meeting"), flag these in `missing_information`, and route the corresponding action items as `REQUIRES_CLARIFICATION` or `CANNOT_EXECUTE`.
2. Do not invent names, emails, meeting dates, or files if not explicitly provided.
3. Populate `requires_human_confirmation` with a list of descriptions of what requires approval.

User request:
{user_request}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WorkInterpretation,
        ),
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    return WorkInterpretation.model_validate_json(response.text)