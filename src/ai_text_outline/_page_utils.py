"""Utilities for page estimation, slicing, and page marker detection."""

from __future__ import annotations

import re


def estimate_total_pages(text: str, chars_per_page: int = 2000) -> int:
    """
    Estimate total pages based on character count.

    Args:
        text: Full text content
        chars_per_page: Average characters per page

    Returns:
        Estimated page count (minimum 1)
    """
    return max(1, len(text) // chars_per_page)


def get_toc_slice(text: str, chars_per_page: int = 2000) -> str:
    """
    Get the portion of text to send to LLM for ToC extraction.

    Used as fallback when དཀར་ཆག (dkar chag) is not found.

    Args:
        text: Full text content
        chars_per_page: Characters per page

    Returns:
        Text slice: first quarter if <1000 pages, else first 100 pages
    """
    total_pages = estimate_total_pages(text, chars_per_page)
    if total_pages < 1000:
        # First quarter
        end = len(text) // 4
    else:
        # First 100 pages
        end = min(100 * chars_per_page, len(text))
    return text[:end]


def find_page_markers(text: str) -> list[tuple[int, int]]:
    """
    Find page number annotations/tags in text.

    Detects patterns like: [1], (1), 【1】, and variants.

    Args:
        text: Full text content

    Returns:
        List of (page_number, char_position) tuples, sorted by position
    """
    markers = []

    # Regex patterns for various page number formats
    patterns = [
        r'\[(\d+)\]',           # [1]
        r'\((\d+)\)',           # (1)
        r'【(\d+)】',           # 【1】
        r'\{(\d+)\}',           # {1}
        r'<page[^>]*?(\d+)[^>]*>',  # <page 1> or variants
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            page_num = int(match.group(1))
            char_pos = match.start()
            markers.append((page_num, char_pos))

    # Sort by position and remove duplicates (by position)
    markers.sort(key=lambda x: x[1])
    # Keep only first occurrence of each position
    unique = []
    seen_pos = set()
    for page, pos in markers:
        if pos not in seen_pos:
            unique.append((page, pos))
            seen_pos.add(pos)

    return unique


def find_toc_section(text: str, chars_per_page: int = 2000) -> str | None:
    """
    Extract the ToC section from text using དཀར་ཆག markers.

    Strategy:
      1. Find all occurrences of དཀར་ཆག (dkar chag)
      2. Start from first occurrence (ToC begin)
      3. End at last occurrence + continue until:
         - Double newline found, OR
         - 4 more pages (~chars_per_page*4) reached
      4. Return the extracted section

    Args:
        text: Full text content
        chars_per_page: Characters per page

    Returns:
        Extracted ToC section, or None if དཀར་ཆག not found
    """
    # དཀར་ཆག is the Tibetan term for "table of contents"
    marker = "དཀར་ཆག"

    # Find all occurrences
    positions = []
    start = 0
    while True:
        pos = text.find(marker, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + len(marker)

    if not positions:
        return None

    # Start from first occurrence
    toc_start = positions[0]

    # End search from last occurrence
    toc_end_anchor = positions[-1]

    # Search for double newline after the anchor
    search_start = toc_end_anchor + len(marker)
    double_newline_pos = text.find("\n\n", search_start)

    if double_newline_pos != -1:
        # Found double newline, stop there
        toc_end = double_newline_pos
    else:
        # No double newline, take 4 more pages
        toc_end = min(search_start + 4 * chars_per_page, len(text))

    return text[toc_start:toc_end]
