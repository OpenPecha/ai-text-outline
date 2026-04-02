"""Gemini LLM interface."""

from __future__ import annotations

import json
import re


def call_gemini(prompt: str, api_key: str) -> dict[str, int]:
    """Call Gemini and parse ToC response.

    Args:
        prompt: The prompt text to send
        api_key: Gemini API key

    Returns:
        Dictionary mapping title to page number. Empty dict if extraction fails.

    Raises:
        ImportError: If google-generativeai is not installed
        ValueError: If context length is exceeded
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai is not installed. "
            "Install it with: pip install google-generativeai"
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return _parse_response(response.text)
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["context", "token", "quota", "too large", "too long"]):
            raise ValueError(f"Context length exceeded: {e}")
        if any(keyword in error_msg for keyword in ["not found", "no longer available", "not supported"]):
            raise ImportError(f"Model not available: {e}")
        raise


def _parse_response(text: str) -> dict[str, int]:
    """Parse JSON response from LLM.

    Handles markdown code blocks and extracts {"toc": {...}} structure.

    Args:
        text: Raw response text from LLM

    Returns:
        Dictionary mapping title (str) to page number (int). Empty dict on parse error.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()

    # Extract outermost {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}

    try:
        data = json.loads(m.group())
        toc = data.get("toc", {})
        return {str(k): int(v) for k, v in toc.items()}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


def call_gemini_for_indices(prompt: str, api_key: str) -> list[int]:
    """Call Gemini for index selection from candidates.

    Args:
        prompt: The prompt text with ToC and candidates
        api_key: Gemini API key

    Returns:
        List of character indices. Empty list if selection fails.

    Raises:
        ImportError: If google-generativeai is not installed
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai is not installed. "
            "Install it with: pip install google-generativeai"
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return _parse_indices_response(response.text)
    except Exception as e:
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in ["context", "token", "quota", "too large", "too long"]):
            raise ValueError(f"Context length exceeded: {e}")
        if any(keyword in error_msg for keyword in ["not found", "no longer available", "not supported"]):
            raise ImportError(f"Model not available: {e}")
        raise


def _parse_indices_response(text: str) -> list[int]:
    """Parse JSON response with indices from LLM.

    Handles markdown code blocks and extracts {"indices": [...]} structure.

    Args:
        text: Raw response text from LLM

    Returns:
        List of integer indices. Empty list on parse error.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()

    # Extract outermost {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return []

    try:
        data = json.loads(m.group())
        indices = data.get("indices", [])
        return [int(i) for i in indices]
    except (json.JSONDecodeError, ValueError, TypeError):
        return []
