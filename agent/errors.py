"""Turn OpenAI errors into a short message with the next step."""

import openai

BILLING_URL = "https://platform.openai.com/settings/organization/billing/"


def describe_openai_error(error: openai.OpenAIError) -> str:
    """A one-line explanation and next step for common OpenAI errors."""
    if isinstance(error, openai.RateLimitError):
        if getattr(error, "code", None) == "insufficient_quota" or "credits" in str(error):
            return f"the OpenAI account has no credits left. Add credits at {BILLING_URL}"
        return "OpenAI rate limit reached. Wait a minute and run again."
    if isinstance(error, openai.AuthenticationError):
        return "OPENAI_API_KEY in .env is missing or invalid."
    if isinstance(error, openai.NotFoundError):
        return "the model was not found. Check OPENAI_MODEL in .env."
    if isinstance(error, openai.APIConnectionError):
        return "couldn't reach the OpenAI API. Check your internet connection."
    return f"OpenAI error: {error}"
