"""Prompt templates for ToC extraction."""

from __future__ import annotations


def get_toc_extraction_prompt(text_slice: str) -> str:
    """
    Generate prompt for extracting Table of Contents from Tibetan text.

    Args:
        text_slice: The text content to analyze

    Returns:
        Formatted prompt string with explicit JSON-only instructions
    """
    return f"""You are analyzing a Tibetan text document to extract the Table of Contents (དཀར་ཆག).

TASK:
Look for a structured list of chapter/section titles paired with page numbers.
The Table of Contents is typically near the beginning of the text.

KEY DETAILS:
- Chapter titles will be in Tibetan script (Unicode block U+0F00-U+0FFF)
- Page numbers may be in Arabic numerals (0-9) or Tibetan numerals (༠-༩)
- Delimiters between titles and page numbers include: ༎ ། . … or spaces
- ToC often begins with དཀར་ཆག or དཀར་ཆགsection markers

RETURN FORMAT - CRITICAL:
- Return ONLY a JSON object. No explanations, no markdown, no extra text.
- Format: {{"toc": {{"chapter_title_1": page_number_1, "chapter_title_2": page_number_2, ...}}}}
- If you cannot find a Table of Contents, return exactly: {{"toc": {{}}}}
- Page numbers must be integers.
- Preserve the original Tibetan text of each title exactly as it appears.

TEXT TO ANALYZE:
---
{text_slice}
---

RESPOND WITH JSON ONLY:"""
