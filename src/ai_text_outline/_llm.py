"""Multi-provider LLM abstraction with lazy imports."""

from __future__ import annotations

import logging

from ._config import Config, Provider

logger = logging.getLogger(__name__)


def call_llm(prompt: str, config: Config) -> str:
    """
    Call the appropriate LLM provider.

    Dispatches to Gemini, OpenAI, or Claude based on config.provider.

    Args:
        prompt: The prompt text to send
        config: Configuration with provider and API key

    Returns:
        Raw text response from LLM

    Raises:
        ImportError: If the provider SDK is not installed
        Exception: On API errors (rate limit, auth, etc.)
    """
    if config.provider == Provider.GEMINI:
        return _call_gemini(prompt, config.model, config.api_key)
    elif config.provider == Provider.OPENAI:
        return _call_openai(prompt, config.model, config.api_key)
    elif config.provider == Provider.CLAUDE:
        return _call_claude(prompt, config.model, config.api_key)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


def _call_gemini(prompt: str, model: str, api_key: str) -> str:
    """Call Google Gemini API. Lazy import of google-generativeai."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai is not installed. "
            "Install it with: pip install google-generativeai"
        )

    genai.configure(api_key=api_key)
    model_obj = genai.GenerativeModel(model)
    response = model_obj.generate_content(prompt)
    return response.text


def _call_openai(prompt: str, model: str, api_key: str) -> str:
    """Call OpenAI API. Lazy import of openai."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai is not installed. "
            "Install it with: pip install openai"
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content


def _call_claude(prompt: str, model: str, api_key: str) -> str:
    """Call Anthropic Claude API. Lazy import of anthropic."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError(
            "anthropic is not installed. "
            "Install it with: pip install anthropic"
        )

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    return response.content[0].text
