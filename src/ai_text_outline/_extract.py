"""Main extraction pipeline."""

from __future__ import annotations

import os
import re

from ._llm import call_gemini
from ._prompt import get_toc_extraction_prompt


def extract_toc_indices(
    file_path: str | None = None,
    text: str | None = None,
    *,
    gemini_api_key: str | None = None,
) -> list[int]:
    """Extract Table of Contents indices from Tibetan text.

    Pipeline:
      1. Validate and load input text
      2. Extract ToC section (first 1/5 of text)
      3. Send to Gemini to get ToC titles
      4. Find second occurrence of each title in full text
      5. Return sorted list of indices

    Args:
        file_path: Path to text file (UTF-8 encoded). Mutually exclusive with text.
        text: Raw text string. Mutually exclusive with file_path.
        gemini_api_key: Gemini API key. Falls back to GEMINI_API_KEY env var if None.

    Returns:
        Sorted list of character indices where each ToC section begins.
        Returns empty list if no ToC found.

    Raises:
        ValueError: If neither or both inputs provided, or no API key found.
        FileNotFoundError: If file_path doesn't exist.
        UnicodeDecodeError: If file is not UTF-8 encoded.
    """
    # Validate inputs
    if (file_path is None) == (text is None):
        raise ValueError("Provide exactly one of file_path or text")

    # Load text from file if needed
    if file_path:
        with open(file_path, encoding="utf-8") as f:
            text = f.read()

    # Resolve API key
    api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "No Gemini API key. Set GEMINI_API_KEY env var or pass gemini_api_key="
        )

    # Extract ToC section (first 1/5 of text)
    toc_section = text[: len(text) // 5]

    # Get ToC titles from Gemini
    prompt = get_toc_extraction_prompt(toc_section)
    toc_dict = call_gemini(prompt, api_key)

    if not toc_dict:
        return []

    # Find second occurrence of each title in full text
    indices = []
    for title in toc_dict:
        matches = list(re.finditer(re.escape(title), text))
        if len(matches) >= 2:
            indices.append(matches[1].start())

    return sorted(indices)
