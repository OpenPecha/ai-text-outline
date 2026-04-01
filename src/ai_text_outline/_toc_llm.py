"""LLM-based ToC extraction with JSON parsing."""

from __future__ import annotations

import json
import logging
import re

from ._config import Config
from ._llm import call_llm
from ._prompt import get_toc_extraction_prompt

logger = logging.getLogger(__name__)


def extract_toc_llm(text_slice: str, config: Config) -> dict[str, int]:
    """
    Send text to LLM and extract ToC as JSON.

    Args:
        text_slice: Text content to analyze (ToC section or fallback slice)
        config: Configuration with LLM provider/model info

    Returns:
        Dictionary {title: page_number}, or empty dict if no ToC found or error
    """
    try:
        prompt = get_toc_extraction_prompt(text_slice)
        response = call_llm(prompt, config)
        toc_data = _parse_llm_response(response)
        return toc_data
    except Exception as e:
        logger.warning(f"LLM ToC extraction failed: {e}")
        return {}


def _parse_llm_response(response: str) -> dict[str, int]:
    """
    Parse JSON from LLM response.

    Handles:
      - Clean JSON
      - JSON wrapped in markdown code blocks (```json ... ```)
      - Extraneous text before/after JSON

    Args:
        response: Raw LLM response text

    Returns:
        Parsed dictionary, or empty dict if parsing fails
    """
    # Try to extract JSON from markdown code blocks first
    markdown_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
    if markdown_match:
        json_str = markdown_match.group(1)
    else:
        json_str = response

    # Try to find and parse JSON object
    # Look for { ... } pattern
    brace_match = re.search(r'\{.*\}', json_str, re.DOTALL)
    if brace_match:
        json_str = brace_match.group(0)

    try:
        data = json.loads(json_str)
        # Extract the "toc" field if it exists
        if isinstance(data, dict) and "toc" in data:
            toc = data["toc"]
            # Ensure all values are integers
            if isinstance(toc, dict):
                result = {}
                for key, val in toc.items():
                    if isinstance(val, int):
                        result[key] = val
                    elif isinstance(val, str):
                        try:
                            result[key] = int(val)
                        except ValueError:
                            logger.warning(f"Could not parse page number for '{key}': {val}")
                return result
        return {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from LLM response: {e}")
        logger.debug(f"Raw response: {response}")
        return {}
