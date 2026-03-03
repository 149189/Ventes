"""Google Gemini API client for generating sales bot responses."""
import logging
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)

# Maximum retries when rate-limited (free tier = 20 req/min)
_MAX_RETRIES = 3


def generate_response(system_prompt: str, conversation_history: list[dict], rag_context: str) -> tuple[str, int]:
    """Generate a response using Google Gemini chat completion.

    Includes automatic retry with backoff for 429 rate-limit errors.

    Returns:
        tuple of (response_text, tokens_used)
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # Build a compact system instruction.
    # When rag_context is empty (greeting/qualifying stages) we omit the
    # products block entirely so the model focuses on the conversation.
    if rag_context:
        product_block = (
            "\nPRODUCTS (only reference these, nothing else):\n"
            f"{rag_context}\n"
        )
    else:
        product_block = (
            "\nNo products loaded yet — do NOT recommend or name any products. "
            "Focus on understanding what the customer wants.\n"
        )

    system_instruction = (
        f"{system_prompt}\n"
        f"{product_block}\n"
        "RULES:\n"
        "- This is WhatsApp. Keep replies under 150 words, 2-3 sentences max.\n"
        "- Use simple English or Hinglish. No markdown, no bullet points.\n"
        "- Always finish sentences completely.\n"
        "- Currency is INR (Rs.). Never use $.\n"
        "- Do NOT invent product names, specs, or prices."
    )

    # Convert conversation history to Gemini format
    gemini_history = []
    for msg in conversation_history[-10:]:
        role = 'model' if msg['role'] == 'assistant' else 'user'
        text = msg.get('content', '').strip()
        if text:
            gemini_history.append({
                'role': role,
                'parts': [{'text': text}],
            })

    # Gemini requires the last message to be from the user.
    if not gemini_history or gemini_history[-1]['role'] != 'user':
        user_text = ''
        for msg in reversed(conversation_history[-10:]):
            if msg['role'] == 'user':
                user_text = msg['content']
                break
        contents = user_text or 'Hello'
    else:
        contents = gemini_history

    # Retry loop for rate-limiting
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=256,
                    temperature=0.7,
                    # Disable internal thinking — not needed for short
                    # WhatsApp replies and it eats the output token budget.
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )

            reply = (response.text or '').strip()

            tokens_used = 0
            if response.usage_metadata:
                tokens_used = (
                    (response.usage_metadata.prompt_token_count or 0)
                    + (response.usage_metadata.candidates_token_count or 0)
                )
            logger.info(f"Gemini response generated ({tokens_used} tokens)")
            return reply, tokens_used

        except Exception as e:
            error_msg = str(e)
            error_lower = error_msg.lower()

            # Retry on rate-limit (429) or transient server errors (503)
            if '429' in error_msg or 'resource_exhausted' in error_lower or '503' in error_msg or 'unavailable' in error_lower:
                wait = _parse_retry_delay(error_msg, default=5 * (attempt + 1))
                logger.warning(
                    f"Gemini transient error (attempt {attempt + 1}/{_MAX_RETRIES}), "
                    f"retrying in {wait}s..."
                )
                time.sleep(wait)
                continue

            if 'quota' in error_lower or 'rate' in error_lower:
                logger.error(f"Gemini quota error: {e}")
                return "I'm a bit busy right now! Let me connect you with our team for immediate help.", 0

            logger.error(f"Gemini API error: {e}")
            raise

    # All retries exhausted
    logger.error(f"Gemini rate limit: all {_MAX_RETRIES} retries exhausted")
    return "I'm a bit busy right now! Let me connect you with our team for immediate help.", 0


def _parse_retry_delay(error_msg: str, default: float = 10.0) -> float:
    """Extract the retry delay from a Gemini 429 error message."""
    # Look for patterns like "retryDelay': '22s'" or "Please retry in 22.23s"
    match = re.search(r'retry\w*[\'"\s:]+(\d+\.?\d*)\s*s', error_msg, re.IGNORECASE)
    if match:
        delay = float(match.group(1))
        # Cap at 30 seconds to avoid hanging forever
        return min(delay + 1, 30.0)
    return default
