"""Main extraction pipeline."""

from __future__ import annotations

import os
import re

from ._llm import call_gemini, call_gemini_for_indices
from ._prompt import get_toc_extraction_prompt, get_index_selection_prompt


def _detect_page_pattern(text: str, toc_dict: dict[str, int], after_index: int) -> str | None:
    """Detect page-number pattern in text.

    Tries patterns against a sample of ToC page numbers.
    Returns the first pattern that matches ≥50% of sampled pages, or None.

    Args:
        text: Full text to search in
        toc_dict: ToC mapping {title: page_number}
        after_index: Character index after which to search (ToC boundary)

    Returns:
        Pattern template string (e.g. "^-{n}-$") or None if no pattern detected.
    """
    if not toc_dict:
        return None

    search_region = text[after_index:]
    candidates = [
        r"^-{n}-$",       # e.g. -5-
        r"^\s*{n}\s*$",   # e.g. standalone 170
    ]
    sample = sorted(set(toc_dict.values()))[:6]  # Check up to 6 page numbers

    for tmpl in candidates:
        hits = sum(
            1 for p in sample
            if re.search(tmpl.format(n=p), search_region, re.MULTILINE)
        )
        if hits >= max(1, len(sample) // 2):
            return tmpl
    return None


def _find_page_marker_positions(
    text: str, page_num: int, pattern: str, after_index: int
) -> list[int]:
    """Find all positions of a page marker in text.

    Args:
        text: Full text
        page_num: Page number to search for
        pattern: Regex pattern template with {n} placeholder
        after_index: Only search after this character index

    Returns:
        List of character indices where page marker ends (position after marker).
    """
    regex = pattern.format(n=page_num)
    search_region = text[after_index:]
    matches = list(re.finditer(regex, search_region, re.MULTILINE))
    # Return the end position (after marker), adjusted for search_region offset
    return [after_index + m.end() for m in matches]


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
      4. Detect page-number pattern (e.g., -N-, or standalone N)
      5. For each section, find page N-1 marker → use position after it
      6. Fallbacks: if page not found → title matching; if multiple pages → LLM call 2
      7. Return sorted list of indices

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

    # Step 1-2: Try extracting ToC with progressively smaller text slices
    fractions = [5, 10, 100]
    toc_dict = {}

    for fraction in fractions:
        try:
            toc_section = text[: len(text) // fraction]
            prompt1 = get_toc_extraction_prompt(toc_section)
            toc_dict = call_gemini(prompt1, api_key)
            break
        except ValueError as e:
            if "context" not in str(e).lower():
                raise
            if fraction == fractions[-1]:
                return []
            continue

    if not toc_dict:
        return []

    # Find ToC boundary using last title's first title occurrence
    # (fallback to ensure we have a boundary marker)
    last_title = max(toc_dict, key=lambda t: toc_dict[t])
    last_title_matches = [
        m.start() for m in re.finditer(re.escape(last_title), text)
    ]

    if not last_title_matches:
        return []

    last_toc_title_index = last_title_matches[0]

    # Step 4: Detect page-number pattern
    page_pattern = _detect_page_pattern(text, toc_dict, last_toc_title_index)

    # Track sections for potential LLM fallback and title-match fallback
    llm_fallback_candidates = {}
    title_fallback_titles = []
    confirmed_indices = {}

    # Process each title in page-number order
    for title in sorted(toc_dict.keys(), key=lambda t: toc_dict[t]):
        page_num = toc_dict[title]
        min_page = min(toc_dict.values())

        # First section: use ToC boundary
        if page_num == min_page:
            confirmed_indices[title] = last_toc_title_index
            continue

        # Other sections: use page N-1 marker
        if page_pattern:
            target_page = page_num - 1
            positions = _find_page_marker_positions(
                text, target_page, page_pattern, last_toc_title_index
            )

            if len(positions) == 0:
                # No page marker found, fall back to title matching
                title_fallback_titles.append(title)
            elif len(positions) == 1:
                # Unique page marker, use it
                confirmed_indices[title] = positions[0]
            else:
                # Multiple matches, fall back to LLM
                llm_fallback_candidates[title] = positions
        else:
            # No pattern detected, fall back to title matching
            title_fallback_titles.append(title)

    # Fallback A: Title matching for sections with no page marker
    for title in title_fallback_titles:
        matches = [
            m.start()
            for m in re.finditer(re.escape(title), text)
            if m.start() >= last_toc_title_index
        ]
        if matches:
            confirmed_indices[title] = matches[0]

    # Fallback B: LLM call 2 for sections with multiple page matches
    if llm_fallback_candidates:
        # Reconstruct candidates dict for LLM (title -> list of positions)
        # and call Gemini 2 to disambiguate
        prompt2 = get_index_selection_prompt(
            toc_dict, llm_fallback_candidates, last_toc_title_index
        )
        llm_indices = call_gemini_for_indices(prompt2, api_key)

        # Merge LLM results into confirmed indices
        for llm_idx in llm_indices:
            # Find which title this index belongs to
            for title, positions in llm_fallback_candidates.items():
                if llm_idx in positions:
                    confirmed_indices[title] = llm_idx
                    break

    # Return sorted indices for all successfully found sections
    return sorted(confirmed_indices.values())
