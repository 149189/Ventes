"""OpenAI API client for generating sales bot responses."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def generate_response(system_prompt: str, conversation_history: list[dict], rag_context: str) -> tuple[str, int]:
    """Generate a response using OpenAI chat completion.

    Returns:
        tuple of (response_text, tokens_used)
    """
    import openai

    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build messages array
    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n\n"
                f"--- Available Products ---\n"
                f"{rag_context}\n"
                f"--- End Products ---\n\n"
                "IMPORTANT: Only reference products listed above. "
                "Keep response under 3 sentences. Be warm and conversational."
            ),
        },
    ]

    # Add conversation history (last 20 messages)
    messages.extend(conversation_history[-20:])

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )

        reply = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else 0
        logger.info(f"OpenAI response generated ({tokens_used} tokens)")
        return reply, tokens_used

    except openai.RateLimitError:
        logger.error("OpenAI rate limit hit")
        return "I'm a bit busy right now! Let me connect you with our team for immediate help.", 0

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
