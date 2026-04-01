"""Regex-based ToC extraction from Tibetan texts."""

from __future__ import annotations

import re


def extract_toc_regex(text: str) -> dict[str, int] | None:
    """
    Try to extract ToC entries from text using regex patterns.

    Looks for structured patterns like:
      - Tibetan text + parenthesized page number: text...…(123)
      - Tibetan text + non-parenthesized number: text 123

    Args:
        text: Text content (typically the extracted ToC section)

    Returns:
        Dictionary {title: page_number} if entries found, None otherwise
    """
    toc = {}

    # Join multi-line entries by looking for:
    # - Lines ending without closing punctuation + next line with Tibetan
    # - Collect consecutive Tibetan lines + following page number

    lines = text.split('\n')
    current_title = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if line contains page number in parentheses: (123)
        paren_match = re.search(r'\((\d+)\)', line_stripped)
        if paren_match:
            page_num = int(paren_match.group(1))

            # Extract title from current accumulated lines + this line
            if current_title:
                # Use the accumulated lines
                title = ' '.join(current_title)
                if title:
                    toc[title.strip()] = page_num
                current_title = []

            # Also try to extract from this line if it has Tibetan text before the number
            before_paren = line_stripped[:paren_match.start()].strip()
            if before_paren and any('\u0F00' <= c <= '\u0FFF' for c in before_paren):
                toc[before_paren] = page_num

        # Check if line has Tibetan text (might be part of a title)
        elif any('\u0F00' <= c <= '\u0FFF' for c in line_stripped):
            # Remove trailing punctuation for cleaner title
            clean_line = re.sub(r'[།.…]+$', '', line_stripped).strip()
            if clean_line:
                current_title.append(clean_line)

    return toc if toc else None


def _tibetan_numeral_to_arabic(tibetan: str) -> str:
    """
    Convert Tibetan numerals to Arabic numerals.

    Tibetan numerals: ༠༡༢༣༤༥༦༧༨༩ (U+0F20 - U+0F29)

    Args:
        tibetan: String of Tibetan numerals

    Returns:
        String of Arabic numerals
    """
    mapping = {
        '༠': '0', '༡': '1', '༢': '2', '༣': '3', '༤': '4',
        '༥': '5', '༦': '6', '༧': '7', '༨': '8', '༩': '9',
    }
    result = ''
    for char in tibetan:
        result += mapping.get(char, char)
    return result
