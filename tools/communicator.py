import os
from google import genai

def draft_communication(recipient: str, context: str) -> str:
    """
    Drafts a professional email or message based on a recipient and context.
    Uses Gemini API to construct the draft.
    """
    if not recipient:
        return "Failed to draft: Recipient information is missing."
    if not context:
        return "Failed to draft: Drafting context is missing."

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Failed to draft: GEMINI_API_KEY is not configured."

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a professional business communicator. Write a polished, professional email or chat draft based on the context and recipient provided.

Recipient: {recipient}
Context/Instructions: {context}

Requirements:
- Professional tone
- Clear subject line (if email format is appropriate)
- Explicit placeholder brackets (e.g. [My Name]) for details that the user must fill in.
- Do NOT output any explanation, markdown formatting outside of the draft itself, or conversational fluff. Just return the drafted communication text.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Failed to draft communication due to LLM error: {str(e)}"
