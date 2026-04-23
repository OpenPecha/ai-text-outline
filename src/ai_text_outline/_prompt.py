"""Prompt templates for ToC extraction and index selection."""

from __future__ import annotations

import json


def get_toc_extraction_prompt(text_slice: str) -> str:
    """
    Generate prompt for extracting Table of Contents from Tibetan text.

    Args:
        text_slice: The text content to analyze

    Returns:
        Formatted prompt string with few-shot examples and JSON-only instructions
    """
    return f"""You are extracting the Table of Contents (དཀར་ཆག) from a Tibetan text.

## Task

Find ALL chapter/section titles paired with their page numbers from the དཀར་ཆག section(s).
Return them as a JSON object.

## Key patterns in Tibetan ToCs

- The header དཀར་ཆག (or དཀར་ཆག །) may appear MULTIPLE TIMES — once per page of the ToC. Extract titles from ALL pages.
- Titles are in Tibetan script. They may wrap across multiple lines.
- Page numbers appear as Tibetan numerals (༡, ༢༦, ༡༠༢) or Arabic numerals (1, 26, 102).
- Page numbers may be preceded by dots, dashes, spaces, or other delimiters: ......༦༩, .34, -280, ........༡༠༢
- OCR noise is common: random English/Chinese characters, asterisks (****), tildes (~1~, ~2~), garbled text. IGNORE these artifacts.
- A title line may be followed by its page number on the SAME line or on the NEXT line.

## Example 1: Multi-page ToC with Tibetan numerals

Input text:
```
དཀར་ཆག །
ཐུགས་ཆེན་འཁོར་བ་དོང་སྤྲུགས་ཀྱི། བརྒྱུད་འདེབས་
བྱིན་རླབས་མཆོག་སྦྱིན།
འཕགས་མཆོག་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་སྔོན་གཏོར།
འཕགས་མཆོག་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་བྱིན་འབེབས།
ཐུགས་ཆེན་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་སྨན་མཆོད།
༡
.༦
༢༦
༣༡
༣༨
~1~

དཀར་ཆག །
རིགས་འདུས་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་སྦྱང་ཆོག་
ཐར་ལམ་འདྲེན་པའི་ཤིང་རྟ།
སྲེག་སྦྱོང་ཡེ་ཤེས་འོད་ཕུང༌།
༥༠
༥༨
```

Expected output:
```json
{{"toc": {{"ཐུགས་ཆེན་འཁོར་བ་དོང་སྤྲུགས་ཀྱི། བརྒྱུད་འདེབས་བྱིན་རླབས་མཆོག་སྦྱིན།": 1, "འཕགས་མཆོག་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་སྔོན་གཏོར།": 6, "འཕགས་མཆོག་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་བྱིན་འབེབས།": 26, "ཐུགས་ཆེན་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་སྨན་མཆོད།": 31, "རིགས་འདུས་འཁོར་བ་དོང་སྤྲུགས་ཀྱི་སྦྱང་ཆོག་ཐར་ལམ་འདྲེན་པའི་ཤིང་རྟ།": 50, "སྲེག་སྦྱོང་ཡེ་ཤེས་འོད་ཕུང༌།": 58}}}}
```

Note: Titles that wrap across lines are joined. Page numbers ༡=1, ༦=6, ༢༦=26, etc. The ~1~ page separator is OCR noise, ignored.

## Example 2: Single-page ToC with Arabic numerals and dashes

Input text:
```
དཀར་ཆག
ཕྱག་རྒྱ་ཆེན་པོ་ལྔ་ལྡན་གྱི་གཏོར་དབང་ཡིད་བཞིན་ནོར་བུ།
ཕྱག་རྒྱ་ཆེན་པོ་ལྔ་ལྡན་གྱི་གསོལ་འདེབས།
ཕྱག་རྒྱ་ཆེན་པོ་ལྔ་ལྡན་གྱི་ཁྲིད་ཀྱི་མན་ངག་རྡོ་རྗེའི་ཚིག་རྐང༌།
--01
-21
-24
```

Expected output:
```json
{{"toc": {{"ཕྱག་རྒྱ་ཆེན་པོ་ལྔ་ལྡན་གྱི་གཏོར་དབང་ཡིད་བཞིན་ནོར་བུ།": 1, "ཕྱག་རྒྱ་ཆེན་པོ་ལྔ་ལྡན་གྱི་གསོལ་འདེབས།": 21, "ཕྱག་རྒྱ་ཆེན་པོ་ལྔ་ལྡན་གྱི་ཁྲིད་ཀྱི་མན་ངག་རྡོ་རྗེའི་ཚིག་རྐང༌།": 24}}}}
```

Note: --01 means page 1, -21 means page 21. Dashes and leading zeros are OCR artifacts.

## Rules

- Extract ONLY the main chapter/section titles from the དཀར་ཆག, not sub-sections or inline references.
- If a title wraps across multiple lines, join them into one string (preserving the Tibetan text).
- Convert ALL page numbers to integers (Tibetan numerals → Arabic: ༡=1, ༡༠༢=102, etc.).
- Ignore OCR noise: asterisks, tildes, random Latin/Chinese characters, garbled text.
- If you cannot find a Table of Contents, return exactly: {{"toc": {{}}}}

## Return format

Return ONLY a JSON object. No explanations, no markdown fences, no extra text.
Format: {{"toc": {{"title_1": page_number_1, "title_2": page_number_2, ...}}}}

## Text to analyze

{text_slice}

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


def get_no_marker_chapter_prompt(candidates: list[dict]) -> str:
    """Prompt for confirming chapter-title pages in a pecha without a ToC marker.

    Used when the text has no ``དཀར་ཆག`` section but instead encodes chapter
    breaks as short (1-3 line) title pages in pecha format. Each candidate is
    a short-line page; a page image is attached in the same order.

    Args:
        candidates: List of dicts with keys ``char_start``, ``title``,
            ``pnum``, ``pname`` (output of ``_find_short_line_pages``). Must
            be aligned with the image list passed to the LLM in the same order.

    Returns:
        Formatted prompt string. The model must return:
        ``{"confirmed_indices": [char_start_1, char_start_2, ...]}``
    """
    lines = []
    for i, c in enumerate(candidates, start=1):
        title = c.get("title", "").replace("\n", " ")
        lines.append(
            f"{i}. char_start={c['char_start']} | text: {title}"
        )
    listing = "\n".join(lines) if lines else "(none)"

    return f"""You are analysing a Tibetan pecha-style text that has NO table of \
contents (དཀར་ཆག) section.

Chapter breaks in this document are marked by short pages — pages that contain \
only 1-3 lines of Tibetan text. Some of those short pages are genuine chapter \
TITLE pages; others are chapter endings (colophons), blank-ish pages adjacent to \
a title, or stray short pages that are not chapter boundaries.

## Inputs

Below are {len(candidates)} candidate short-line pages identified from the OCR. \
For each candidate I also attach its page IMAGE, in the SAME ORDER as the list.

Candidates (index, char_start, text content):
{listing}

## Visual cues (how to tell a title page from an ending / noise)

- Chapter TITLE page: the Tibetan text is CENTERED horizontally on the folio and \
  is usually 1-3 lines only. Often has honorific marks / decoration. NO dense \
  running text above or below.
- Chapter ENDING (colophon): a few lines flush to the TOP-LEFT of the folio, \
  usually following dense body text on the preceding page. Not a title.
- Blank / near-blank page adjacent to a title page: NOT itself a title.
- If you cannot decide from the image, DO NOT include it.

## Task

For each candidate, look at its IMAGE and decide if it is the START of a new \
chapter in this pecha. Return ONLY the ``char_start`` values of the confirmed \
chapter-start pages.

## Output format

Return ONLY a JSON object on a single line. No explanation, no markdown fences:

```json
{{"confirmed_indices": [char_start_a, char_start_b, ...]}}
```

Rules:
- Values must be integers drawn from the ``char_start`` column above.
- Keep them in ascending order.
- Omit any candidate that is not a confirmed chapter title.
- If nothing is a confirmed chapter title, return ``{{"confirmed_indices": []}}``.

RESPOND WITH JSON ONLY:"""


def get_vision_toc_extraction_prompt(text_slice: str) -> str:
    """
    Generate prompt for extracting ToC using both OCR text and page images.

    This prompt is used when page images are available alongside the OCR text.
    The LLM can cross-reference the images with the text to correct OCR errors.

    Args:
        text_slice: The OCR text content of the ToC region

    Returns:
        Formatted prompt string for multimodal (text + images) ToC extraction
    """
    return f"""You are extracting the Table of Contents (དཀར་ཆག) from a Tibetan text.

You are provided with:
1. The OCR text of the ToC section (below)
2. Page images of the actual ToC pages (attached)

## IMPORTANT: Use images as source of truth

The OCR text may have errors:
- Misaligned titles and page numbers (a title's page number may appear on wrong line)
- Overlapping text where titles and numbers are merged
- Garbled characters, random Latin/Chinese/Arabic script mixed in
- Missing or duplicated lines

The page images show the ORIGINAL layout. Use them to:
- Verify which titles belong to which page numbers
- Correct any OCR misalignment between titles and their page numbers
- Identify titles that the OCR may have garbled or split incorrectly
- Read page numbers directly from the images when OCR numbers seem wrong

## Task

Find ALL chapter/section titles paired with their page numbers from the དཀར་ཆག section(s).
Return them as a JSON object.

## Key patterns in Tibetan ToCs

- The header དཀར་ཆག (or དཀར་ཆག །) may appear MULTIPLE TIMES — once per page of the ToC. Extract titles from ALL pages.
- Titles are in Tibetan script. They may wrap across multiple lines.
- Page numbers appear as Tibetan numerals (༡, ༢༦, ༡༠༢) or Arabic numerals (1, 26, 102).
- Page numbers may be preceded by dots, dashes, spaces, or other delimiters.
- A title line may be followed by its page number on the SAME line or on the NEXT line.
- The ToC typically lists titles on the left and page numbers on the right side of the page.

## Rules

- Extract ONLY the main chapter/section titles from the དཀར་ཆག, not sub-sections or inline references.
- If a title wraps across multiple lines, join them into one string (preserving the Tibetan text).
- Convert ALL page numbers to integers (Tibetan numerals → Arabic: ༡=1, ༡༠༢=102, etc.).
- Ignore OCR noise: asterisks, tildes, random Latin/Chinese characters, garbled text.
- Cross-reference the OCR text with the page images to ensure accuracy.
- If you cannot find a Table of Contents, return exactly: {{"toc": {{}}}}

## Return format

Return ONLY a JSON object. No explanations, no markdown fences, no extra text.
Format: {{"toc": {{"title_1": page_number_1, "title_2": page_number_2, ...}}}}

## OCR Text of ToC section

{text_slice}

RESPOND WITH JSON ONLY:"""
