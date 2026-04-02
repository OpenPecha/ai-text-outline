"""Prompt templates for ToC extraction and index selection."""

from __future__ import annotations

import json


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


def get_index_selection_prompt(
    toc_dict: dict[str, int],
    candidates: dict[str, list[int]],
    last_toc_title_index: int,
) -> str:
    """
    Generate prompt for selecting correct section start indices.

    After extracting ToC titles, this prompt helps LLM identify which character
    index in the full text represents the actual section start (not the ToC entry).

    Args:
        toc_dict: Dictionary mapping title to page number
        candidates: Dictionary mapping title to list of all character indices where title appears
        last_toc_title_index: Character index where last ToC title (by page) first appears (= ToC boundary)

    Returns:
        Formatted prompt string with examples and instructions
    """
    # Sort titles by page number (ascending) to establish order
    toc_order = sorted(toc_dict, key=lambda t: toc_dict[t])

    input_data = {
        "toc_order": toc_order,
        "last_toc_title_index": last_toc_title_index,
        "candidates": candidates,
    }

    return f"""You are given a Tibetan text's Table of Contents (དཀར་ཆག) and, for each ToC title, \
a list of character positions where that title appears in the full text.

Your task: select exactly ONE character index per title — the index where that \
section ACTUALLY BEGINS in the body of the text (NOT where it appears in the ToC itself).

## Background

The ToC appears near the start of the text. Every title listed in the ToC appears \
at least once INSIDE the ToC section itself. The actual chapter content begins AFTER \
the ToC section ends.

The LAST title in the ToC (by page number, i.e., the highest page number) acts as \
an anchor. Its FIRST occurrence in the text is from within the ToC. This position \
(`last_toc_title_index`) marks where the ToC section ends. All actual section starts \
must come AFTER this index.

The chosen indices must also be in ASCENDING ORDER, matching the order of titles in \
the ToC (first section starts before second, second before third, etc.).

## Input Format

```json
{{
  "toc_order": ["Title A", "Title B", "Title C"],
  "last_toc_title_index": 1500,
  "candidates": {{
    "Title A": [100, 5200, 10100],
    "Title B": [150, 12400],
    "Title C": [1500, 22000]
  }}
}}
```

## Output Format

Return ONLY a JSON object on a single line. No explanation, no extra text:

```json
{{"indices": [5200, 12400, 22000]}}
```

The list must:
- Contain only indices greater than `last_toc_title_index`
- Be in ascending order (matching toc_order)
- Skip titles with no valid candidate (do not include null or -1)

## DO

- Pick the FIRST candidate index that is greater than `last_toc_title_index`
- Ensure the final list is in ascending order
- Skip a title entirely if all its candidates are ≤ `last_toc_title_index`
- Include the last title using its SECOND occurrence (first is the ToC entry itself)

## DON'T

- Pick an index ≤ `last_toc_title_index` (that would be inside the ToC)
- Break ascending order
- Include null, -1, or placeholder values
- Return anything other than the JSON object

## Example 1 (Simple)

Input:
```json
{{
  "toc_order": ["Introduction", "Chapter One", "Conclusion"],
  "last_toc_title_index": 820,
  "candidates": {{
    "Introduction": [210, 4100],
    "Chapter One": [250, 7200],
    "Conclusion": [820, 12300]
  }}
}}
```

Reasoning:
- "Conclusion" has the highest page number. Its first occurrence at 820 = ToC anchor.
- All valid indices must be > 820.
- "Introduction": 210 → skip (≤820). 4100 → valid ✓ → pick 4100
- "Chapter One": 250 → skip (≤820). 7200 → valid ✓ → pick 7200
- "Conclusion": 820 → skip (= anchor, ToC entry). 12300 → valid ✓ → pick 12300
- Order: 4100 < 7200 < 12300 ✓

Output:
```json
{{"indices": [4100, 7200, 12300]}}
```

## Example 2 (Edge cases: title appears once, title appears 3 times)

Input:
```json
{{
  "toc_order": ["Preface", "Chapter A", "Chapter B", "Epilogue"],
  "last_toc_title_index": 950,
  "candidates": {{
    "Preface": [180, 3500],
    "Chapter A": [300, 6100, 6120],
    "Chapter B": [600],
    "Epilogue": [950, 18000]
  }}
}}
```

Reasoning:
- "Epilogue" has highest page number. First occurrence at 950 = ToC anchor.
- All valid indices must be > 950.
- "Preface": 180 → skip. 3500 → valid ✓ → pick 3500
- "Chapter A": 300 → skip. 6100 → valid ✓ (pick first valid even if 6120 also valid)
- "Chapter B": 600 → skip (≤950). No more candidates → skip this title entirely
- "Epilogue": 950 → skip (= anchor). 18000 → valid ✓ → pick 18000
- Order: 3500 < 6100 < 18000 ✓ (Chapter B skipped, 3 indices for 4 titles is fine)

Output:
```json
{{"indices": [3500, 6100, 18000]}}
```

## Now process the following input:

```json
{json.dumps(input_data, ensure_ascii=False, indent=2)}
```

RESPOND WITH JSON ONLY:"""
