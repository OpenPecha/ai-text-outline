"""Main extraction pipeline."""

from __future__ import annotations

import os
import re

from ._llm import call_gemini, call_gemini_for_indices
from ._prompt import get_toc_extraction_prompt, get_index_selection_prompt


def extract_toc_indices(
    file_path: str | None = None,
    text: str | None = None,
    *,
    gemini_api_key: str | None = None,
) -> list[int]:
    """Extract Table of Contents indices from Tibetan text.

    Pipeline:
      1. Validate and load input text
      2. Extract ToC section (first 1/5 of text, with fallback to 1/10 and 1/100)
      3. Call Gemini 1: Get ToC titles + page numbers
      4. Find all occurrences of each title in full text
      5. Determine ToC boundary using last title's first occurrence
      6. Call Gemini 2: Select correct index for each title
      7. Return sorted list of indices

    Args:
        file_path: Path to text file (UTF-8 encoded). Mutually exclusive with text.
        text: Raw text string. Mutually exclusive with file_path.
        gemini_api_key: Gemini API key. Falls back to GEMINI_API_KEY env var if None.

    Returns:
        Sorted list of character indices where each ToC section begins.
        Returns empty list if no ToC found.

    Note:
        For each title, only the first 10 occurrences are considered to prevent
        context window overflow in large texts. This is sufficient since the first
        occurrence is usually in the ToC and the second in the actual content.

        If the first ToC extraction call exceeds context limits, automatically retries
        with progressively smaller text slices: 1/5 → 1/10 → 1/100.

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

    # Step 1-2: Try extracting ToC with progressively smaller text slices
    # Start with 1/5, fallback to 1/10, then 1/100 if context is exceeded
    fractions = [5, 10, 100]
    toc_dict = {}

    for fraction in fractions:
        try:
            toc_section = text[: len(text) // fraction]
            prompt1 = get_toc_extraction_prompt(toc_section)
            toc_dict = call_gemini(prompt1, api_key)
            break  # Success, stop retrying
        except ValueError as e:
            if "context" not in str(e).lower():
                raise  # Re-raise if not a context error
            if fraction == fractions[-1]:
                # Last attempt failed, return empty
                return []
            # Continue to next fraction

    if not toc_dict:
        return []

    # Step 3: Find all occurrences of each title in full text
    # Truncate to first 10 to prevent context window overflow in Gemini Call 2
    candidates = {}
    for title in toc_dict:
        all_matches = [m.start() for m in re.finditer(re.escape(title), text)]
        candidates[title] = all_matches[:10]  # Keep first 10 occurrences max

    # Step 4: Find ToC boundary (first occurrence of last/highest-page title)
    last_title = max(toc_dict, key=lambda t: toc_dict[t])
    last_title_occurrences = candidates.get(last_title, [])

    if not last_title_occurrences:
        # Can't determine ToC boundary, can't proceed
        return []

    last_toc_title_index = last_title_occurrences[0]

    # Step 5: Call Gemini 2 to select correct index for each title
    prompt2 = get_index_selection_prompt(toc_dict, candidates, last_toc_title_index)
    indices = call_gemini_for_indices(prompt2, api_key)

    return sorted(indices)
