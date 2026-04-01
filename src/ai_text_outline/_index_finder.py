"""Find character indices for ToC section starts."""

from __future__ import annotations

import logging

from rapidfuzz import fuzz

from ._config import Config
from ._page_utils import find_page_markers

logger = logging.getLogger(__name__)


def find_section_indices(
    toc: dict[str, int],
    text: str,
    config: Config,
) -> list[int]:
    """
    For each ToC entry, find the character index where that section starts.

    Strategy:
      1. If page markers exist in text:
         - Find the page number from ToC
         - Locate the page marker
         - Return position of first content after marker
      2. If no page markers:
         - Fuzzy match the title in the text
         - Among matches >= threshold, pick closest to expected offset
         - Skip entries with no match >= threshold

    Args:
        toc: Dictionary {title: page_number} from ToC
        text: Full text content
        config: Configuration with chars_per_page and fuzzy_threshold

    Returns:
        Sorted list of character indices, excluding failed matches
    """
    if not toc:
        return []

    page_markers = find_page_markers(text)
    indices = []

    for title, page_num in toc.items():
        if page_markers:
            # Try to find by page marker first
            idx = _find_by_page_marker(page_num, text, page_markers)
        else:
            # Fallback to fuzzy matching
            idx = _find_by_fuzzy_match(
                title,
                page_num,
                text,
                config.chars_per_page,
                config.fuzzy_threshold,
            )

        if idx is not None:
            indices.append(idx)
        else:
            logger.debug(f"Could not locate ToC entry: {title} (page {page_num})")

    return sorted(indices)


def _find_by_page_marker(page_num: int, text: str, page_markers: list) -> int | None:
    """
    Find section start by page marker.

    Args:
        page_num: Page number to find
        text: Full text
        page_markers: List of (page_number, char_position) tuples

    Returns:
        Character index of first content after page marker, or None if not found
    """
    # Find the page marker matching the page number
    for marked_page, pos in page_markers:
        if marked_page == page_num:
            # Find the first non-whitespace character after this marker
            search_start = pos + 1
            while search_start < len(text) and text[search_start].isspace():
                search_start += 1
            return search_start if search_start < len(text) else None

    return None


def _find_by_fuzzy_match(
    title: str,
    expected_page: int,
    text: str,
    chars_per_page: int,
    threshold: float,
) -> int | None:
    """
    Find section start by fuzzy matching the title.

    Uses rapidfuzz with sliding window, restricted to a search window
    around the expected page offset. Among all matches scoring >= threshold,
    picks the one closest to expected_page * chars_per_page.

    Args:
        title: Section title to find
        expected_page: Expected page number (for position estimation)
        text: Full text
        chars_per_page: Characters per page
        threshold: Fuzzy match threshold (0.0-1.0)

    Returns:
        Character index of best match, or None if no match >= threshold
    """
    if not title or len(title) == 0:
        return None

    # Estimate expected position based on page number
    expected_pos = expected_page * chars_per_page
    total_text_len = len(text)

    # Search window: +/- 50% of expected position
    window_size = int(chars_per_page * 0.5)
    search_start = max(0, expected_pos - window_size)
    search_end = min(total_text_len, expected_pos + window_size)

    # If the search window is very small or we're at the end, expand it
    if search_end - search_start < len(title) * 2:
        search_start = max(0, expected_pos - chars_per_page)
        search_end = min(total_text_len, expected_pos + chars_per_page)

    # Slide a window through the search area and score matches
    title_len = len(title)
    window_size_search = min(title_len + 20, 200)  # Allow some length variation

    best_match = None
    best_score = threshold * 100  # Convert threshold to percentage scale
    best_distance_to_expected = float('inf')

    for i in range(search_start, max(search_start, search_end - window_size_search)):
        window_end = min(i + window_size_search, search_end)
        window = text[i:window_end]

        # Use rapidfuzz partial_ratio for flexible matching
        score = fuzz.partial_ratio(title, window)

        if score >= best_score:
            # If this match is better, or same score but closer to expected pos
            distance_to_expected = abs(i - expected_pos)
            if score > best_score or distance_to_expected < best_distance_to_expected:
                best_score = score
                best_match = i
                best_distance_to_expected = distance_to_expected

    return best_match
