
import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


def generate_reply(
    system_prompt: str,
    messages: list[dict[str, str]],
) -> str:
    """Generate an assistant reply using Gemini."""

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from .env")

    if not model:
        raise RuntimeError("GEMINI_MODEL is missing from .env")

    if not messages:
        raise ValueError("At least one conversation message is required")

    client = genai.Client(api_key=api_key)

    # Convert our stored conversation into Gemini's message format.
    contents = [
        {
            "role": (
                "user" if message["role"] == "user"
                else "model"
            ),
            "parts": [{"text": message["content"]}],
        }
        for message in messages
    ]

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config={
            "system_instruction": system_prompt,
        },
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    return response.text.strip()
