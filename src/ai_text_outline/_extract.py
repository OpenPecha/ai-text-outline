"""Main extraction pipeline."""

from __future__ import annotations

import os
import re

from ._llm import (
    call_gemini,
    call_gemini_for_indices,
    call_gemini_for_no_marker,
)
from ._pages import fetch_page_image, fetch_toc_page_images, get_volume_pages
from ._prompt import (
    get_no_marker_chapter_prompt,
    get_toc_extraction_prompt,
    get_index_selection_prompt,
    get_vision_toc_extraction_prompt,
)

# Regex for "meaningful" Tibetan content in a text line.
# Tibetan Unicode block: U+0F00..U+0FFF
_TIBETAN_LINE_RE = re.compile(r"[\u0F00-\u0FFF]")

# Tibetan digit mapping: ༠༡༢༣༤༥༦༧༨༩
_ARABIC_TO_TIBETAN = str.maketrans("0123456789", "༠༡༢༣༤༥༦༧༨༩")


def _arabic_to_tibetan(n: int) -> str:
    """Convert an Arabic integer to its Tibetan numeral string."""
    return str(n).translate(_ARABIC_TO_TIBETAN)


def _build_index_map(text: str, start: int, end: int, strip_chars: str) -> tuple[str, list[int]]:
    """Build a cleaned version of text[start:end] with an index mapping back to original positions.

    Args:
        text: Full text
        start: Start index in text
        end: End index in text
        strip_chars: Characters to remove (e.g. '\\n\\r' or '།')

    Returns:
        Tuple of (cleaned_text, index_map) where index_map[i] is the original
        position in `text` corresponding to cleaned_text[i].
    """
    cleaned = []
    index_map = []
    for i in range(start, min(end, len(text))):
        if text[i] not in strip_chars:
            cleaned.append(text[i])
            index_map.append(i)
    return "".join(cleaned), index_map


def _refine_index_to_title(
    text: str, marker_pos: int, title: str, next_boundary: int | None = None
) -> int:
    """Refine a page-marker position to the actual title start position.

    Searches for the title in a window after marker_pos, handling newlines
    in the title and extra shed characters (།).

    Args:
        text: Full text
        marker_pos: Character index to start searching from (e.g. end of page marker)
        title: The section title to search for
        next_boundary: Optional upper bound for the search window

    Returns:
        Original text index where the title begins, or marker_pos if not found.
    """
    if not title:
        return marker_pos

    window_end = next_boundary if next_boundary is not None else marker_pos + 5000
    window_end = min(window_end, len(text))

    if marker_pos >= window_end:
        return marker_pos

    # Layer 1: strip newlines → flat text + flat_to_orig mapping
    flat_text, flat_to_orig = _build_index_map(text, marker_pos, window_end, "\n\r")
    if not flat_text:
        return marker_pos

    # Layer 2: strip sheds from flat text → norm text + norm_to_flat mapping
    norm_text, norm_to_flat = _build_index_map(flat_text, 0, len(flat_text), "།")
    if not norm_text:
        return marker_pos

    # Normalize title: strip sheds, then escape for regex
    norm_title = title.replace("།", "")
    if not norm_title:
        return marker_pos

    pattern = re.escape(norm_title)
    m = re.search(pattern, norm_text)
    if m:
        # Map back: norm position → flat position → original position
        flat_idx = norm_to_flat[m.start()]
        return flat_to_orig[flat_idx]

    return marker_pos


def _detect_page_pattern(text: str, toc_dict: dict[str, int], after_index: int) -> tuple[str, str] | None:
    """Detect page-number pattern in text.

    Tries patterns against a sample of ToC page numbers using both Arabic
    and Tibetan numeral systems.
    Returns the first (pattern, numeral_type) that matches ≥50% of sampled pages, or None.

    Args:
        text: Full text to search in
        toc_dict: ToC mapping {title: page_number}
        after_index: Character index after which to search (ToC boundary)

    Returns:
        Tuple of (pattern_template, numeral_type) where numeral_type is "arabic" or
        "tibetan", or None if no pattern detected.
    """
    if not toc_dict:
        return None

    search_region = text[after_index:]
    candidates = [
        r"^-{n}-$",       # e.g. -5- or -༥-
        r"^\s*{n}\s*$",   # e.g. standalone 170 or ༡༧༠
    ]
    sample = sorted(set(toc_dict.values()))[:6]  # Check up to 6 page numbers

    for tmpl in candidates:
        # Try Arabic numerals first
        hits = sum(
            1 for p in sample
            if re.search(tmpl.format(n=p), search_region, re.MULTILINE)
        )
        if hits >= max(1, len(sample) // 2):
            return (tmpl, "arabic")

        # Try Tibetan numerals
        hits = sum(
            1 for p in sample
            if re.search(tmpl.format(n=_arabic_to_tibetan(p)), search_region, re.MULTILINE)
        )
        if hits >= max(1, len(sample) // 2):
            return (tmpl, "tibetan")

    return None


def _find_page_marker_positions(
    text: str, page_num: int, pattern: str, after_index: int,
    numeral_type: str = "arabic",
) -> list[int]:
    """Find all positions of a page marker in text.

    Args:
        text: Full text
        page_num: Page number to search for
        pattern: Regex pattern template with {n} placeholder
        after_index: Only search after this character index
        numeral_type: "arabic" or "tibetan" — determines how page_num is formatted

    Returns:
        List of character indices where page marker ends (position after marker).
    """
    formatted_num = _arabic_to_tibetan(page_num) if numeral_type == "tibetan" else str(page_num)
    regex = pattern.format(n=formatted_num)
    search_region = text[after_index:]
    matches = list(re.finditer(regex, search_region, re.MULTILINE))
    # Return the end position (after marker), adjusted for search_region offset
    return [after_index + m.end() for m in matches]


def _fuzzy_find_title_in_text(
    text: str, title: str, search_start: int,
) -> int | None:
    """Find a title in the text using normalized matching.

    Strips །, whitespace, and newlines from both the text region and the title,
    then searches for a match. Returns the original character index in text
    where the title begins, or None if not found.
    """
    if not title:
        return None

    # Normalize the title: strip sheds, collapse whitespace
    norm_title = title.replace("།", "").replace("\n", "").replace("\r", "")
    norm_title = re.sub(r"\s+", "", norm_title)
    if not norm_title:
        return None

    # Build normalized version of text from search_start with index mapping
    search_region = text[search_start:]
    cleaned_chars = []
    index_map = []
    for i, ch in enumerate(search_region):
        if ch not in "།\n\r \t":
            cleaned_chars.append(ch)
            index_map.append(i)
    cleaned_text = "".join(cleaned_chars)

    pattern = re.escape(norm_title)
    m = re.search(pattern, cleaned_text)
    if m and index_map:
        return search_start + index_map[m.start()]

    return None


def _find_toc_region(text: str) -> tuple[int, int] | None:
    """Find the character range covering the entire ToC region.

    Tibetan texts often have multi-page ToCs where དཀར་ཆག is repeated as a
    header on each page. This function finds all occurrences, identifies the
    cluster of nearby ones (the actual ToC headers vs. body-text mentions),
    and then detects where the ToC ends by looking for body-text patterns
    after the last ToC header.

    Returns:
        Tuple of (toc_start, toc_end) character indices, or None if no marker found.
        toc_start: position of first དཀར་ཆག occurrence.
        toc_end: estimated end of the ToC region (where body text begins).
    """
    markers = [m.start() for m in re.finditer(r"དཀར་ཆག་?", text)]
    if not markers:
        return None

    # Cluster nearby markers: ToC headers are typically close together
    # (within 5% of text length), while body-text mentions are far away.
    toc_start = markers[0]
    cluster_threshold = max(len(text) // 20, 5000)
    toc_markers = [markers[0]]
    for pos in markers[1:]:
        if pos - toc_markers[-1] <= cluster_threshold:
            toc_markers.append(pos)
        else:
            break

    last_toc_header = toc_markers[-1]

    # Detect ToC end: scan after the last དཀར་ཆག header for the transition
    # from ToC entries (title + page number lines) to body text.
    # Heuristic: look for a region after the last header where we stop seeing
    # page-number patterns (Tibetan or Arabic numerals on their own lines).
    # Use the last page number line as the ToC end boundary.
    scan_start = last_toc_header
    scan_end = min(len(text), last_toc_header + max(len(text) // 10, 10000))
    scan_region = text[scan_start:scan_end]

    # Find all lines that look like page numbers (standalone numbers, Tibetan or Arabic)
    page_num_pattern = re.compile(
        r"^[\s.·\-~*༔]*([༠-༩]+|\d+)[\s.·\-~*]*$", re.MULTILINE
    )
    page_num_matches = list(page_num_pattern.finditer(scan_region))

    if page_num_matches:
        # ToC ends after the last page-number line in the scan region
        toc_end = scan_start + page_num_matches[-1].end()
    else:
        # No page numbers found; use a reasonable window after last header
        toc_end = min(len(text), last_toc_header + 5000)

    return (toc_start, toc_end)


def _get_image_bounded_toc_end(
    toc_start: int,
    pages: list[dict],
    n_pages: int = 5,
) -> int | None:
    """Compute a tight ToC end by capping at N consecutive BDRC pages.

    Finds the BDRC page that contains ``toc_start`` and returns the ``cend``
    of the page N-1 pages after it (or the last available page). Used to
    bound the ToC region when ``_find_toc_region()`` stretches it across
    the whole document because of page-number-like noise.

    Args:
        toc_start: Character index where the ToC region starts.
        pages: BDRC page list (dicts with ``cstart``/``cend``/``pname``).
        n_pages: Number of consecutive pages to include (default 5).

    Returns:
        Character index for a tighter ``toc_end``, or ``None`` if the page
        containing ``toc_start`` cannot be located.
    """
    start_idx = next(
        (
            i for i, p in enumerate(pages)
            if p["cstart"] <= toc_start <= p["cend"]
        ),
        None,
    )
    if start_idx is None:
        return None
    end_idx = min(start_idx + n_pages - 1, len(pages) - 1)
    return pages[end_idx]["cend"]


def _find_short_line_pages(
    text: str,
    pages: list[dict],
    max_lines: int = 5,
    min_tibetan_chars: int = 1,
) -> list[dict]:
    """Find BDRC pages whose OCR content has at most ``max_lines`` Tibetan lines.

    These short pages are candidate chapter-title pages for pecha-style
    texts that lack a ``དཀར་ཆག`` marker: each chapter title is a 1-3 line
    page centered on the folio.

    Args:
        text: Full text of the document.
        pages: BDRC page list (dicts with ``cstart``/``cend``/``pnum``/``pname``).
        max_lines: Maximum meaningful Tibetan lines for a candidate page.
        min_tibetan_chars: Minimum Tibetan characters needed for a line to
            count as "meaningful".

    Returns:
        List of candidate dicts with keys ``char_start`` (int), ``title`` (str),
        ``pnum`` (int), ``pname`` (str), sorted by ``char_start``.
    """
    candidates: list[dict] = []
    for page in pages:
        cstart = page.get("cstart")
        cend = page.get("cend")
        if cstart is None or cend is None:
            continue
        page_text = text[cstart:cend]
        lines = page_text.split("\n")
        meaningful: list[str] = []
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if len(_TIBETAN_LINE_RE.findall(line)) >= min_tibetan_chars:
                meaningful.append(line)
        if 1 <= len(meaningful) <= max_lines:
            candidates.append({
                "char_start": cstart,
                "title": " ".join(meaningful),
                "pnum": page.get("pnum"),
                "pname": page.get("pname"),
            })
    candidates.sort(key=lambda c: c["char_start"])
    return candidates


def _get_toc_slice(text: str, toc_region: tuple[int, int], max_chars: int | None = None) -> str:
    """Extract the ToC text with a small buffer before and after.

    Args:
        text: Full text
        toc_region: (toc_start, toc_end) from _find_toc_region
        max_chars: Optional maximum characters. If the region exceeds this,
                   truncate from the end.
    """
    toc_start, toc_end = toc_region
    buffer_before = min(1000, toc_start)
    buffer_after = 500
    slice_start = toc_start - buffer_before
    slice_end = min(len(text), toc_end + buffer_after)

    result = text[slice_start:slice_end]
    if max_chars and len(result) > max_chars:
        result = result[:max_chars]
    return result


def extract_toc_indices(
    file_path: str | None = None,
    text: str | None = None,
    *,
    gemini_api_key: str | None = None,
    volume_id: str | None = None,
    iiif_api_key: str | None = None,
) -> dict:
    """Extract Table of Contents indices from Tibetan text.

    Pipeline:
      1. Validate and load input text
      2. Find ToC via དཀར་ཆག marker, then extract smart slice (fallback: first 1/5)
      3. Call Gemini 1: Get ToC titles + page numbers
      4. Detect page-number pattern (e.g., -N-, or standalone N)
      5. For each section, find page N-1 marker → use position after it
      6. Fallbacks: if page not found → title matching; if multiple pages → LLM call 2
      7. Return sorted list of indices with TOC mapping

    Args:
        file_path: Path to text file (UTF-8 encoded). Mutually exclusive with text.
        text: Raw text string. Mutually exclusive with file_path.
        gemini_api_key: Gemini API key. Falls back to GEMINI_API_KEY env var if None.
        volume_id: BDRC volume identifier for fetching page images (vision mode).
            When provided, ToC page images are sent alongside text to improve accuracy.
        iiif_api_key: IIIF API key for image access. Falls back to IIIF_API_KEY env var.

    Returns:
        Dictionary with keys "breakpoints" and "toc":
        - "breakpoints": sorted list of character indices where each ToC section begins
        - "toc": dictionary mapping title to page number from AI extraction
        Returns {"breakpoints": [], "toc": {}} if no ToC found.

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

    # Resolve IIIF API key for vision mode
    iiif_key = iiif_api_key or os.environ.get("IIIF_API_KEY")

    # Step 1-2: Find ToC region and extract smart slice
    toc_region = _find_toc_region(text)
    toc_dict = {}

    if toc_region is not None:
        # Try vision-enhanced extraction first if volume_id is available
        if volume_id and iiif_key:
            try:
                toc_start, toc_end = toc_region
                # Fetch BDRC page list once; cap ToC end at 5 pages from the
                # page containing toc_start so the window never exceeds the
                # actual ToC even when _find_toc_region() is greedy.
                vol_id = ""
                pages: list[dict] = []
                try:
                    vol_id, pages = get_volume_pages(volume_id)
                except RuntimeError:
                    vol_id, pages = "", []
                if pages and vol_id:
                    bounded_end = _get_image_bounded_toc_end(
                        toc_start, pages, n_pages=5,
                    )
                    if bounded_end is not None:
                        toc_end = min(toc_end, bounded_end)
                        toc_region = (toc_start, toc_end)

                toc_images = fetch_toc_page_images(
                    volume_id, toc_start, toc_end,
                    iiif_api_key=iiif_key,
                    vol_id=vol_id or None,
                    pages=pages or None,
                )
                if toc_images:
                    toc_section = _get_toc_slice(
                        text, toc_region, max_chars=15000,
                    )
                    prompt1 = get_vision_toc_extraction_prompt(toc_section)
                    toc_dict = call_gemini(prompt1, api_key, images=toc_images)
            except (ValueError, RuntimeError):
                # Vision failed; fall through to text-only
                toc_dict = {}

        # Text-only fallback if vision didn't produce results
        if not toc_dict:
            max_chars_attempts = [None, len(text) // 10, len(text) // 50]
            for max_chars in max_chars_attempts:
                try:
                    toc_section = _get_toc_slice(text, toc_region, max_chars=max_chars)
                    prompt1 = get_toc_extraction_prompt(toc_section)
                    toc_dict = call_gemini(prompt1, api_key)
                    break
                except ValueError as e:
                    if "context" not in str(e).lower():
                        raise
                    if max_chars == max_chars_attempts[-1]:
                        return {"breakpoints": [], "toc": {}}
                    continue

    # No-marker detection path: pecha-style texts without a དཀར་ཆག marker.
    # Use BDRC page structure to find short-line "title" pages and confirm
    # them with Gemini using one image per candidate.
    if not toc_dict and toc_region is None and volume_id and iiif_key:
        try:
            vol_id, pages = get_volume_pages(volume_id)
            if pages and vol_id:
                candidates = _find_short_line_pages(text, pages)
                if candidates:
                    candidates = candidates[:30]
                    images: list[bytes] = []
                    kept: list[dict] = []
                    for c in candidates:
                        try:
                            img = fetch_page_image(vol_id, c["pname"], iiif_key)
                        except RuntimeError:
                            continue
                        images.append(img)
                        kept.append(c)
                    if kept and images:
                        prompt = get_no_marker_chapter_prompt(kept)
                        confirmed = call_gemini_for_no_marker(
                            prompt, api_key, images=images,
                        )
                        if confirmed:
                            return {
                                "breakpoints": sorted(set(confirmed)),
                                "toc": {},
                            }
        except (ValueError, RuntimeError):
            pass

    if not toc_dict:
        # Fallback: no marker found or marker-based extraction returned empty.
        # Try the original approach with progressively smaller slices from the start.
        for fraction in [5, 10, 100]:
            try:
                toc_section = text[: len(text) // fraction]
                prompt1 = get_toc_extraction_prompt(toc_section)
                toc_dict = call_gemini(prompt1, api_key)
                break
            except ValueError as e:
                if "context" not in str(e).lower():
                    raise
                if fraction == 100:
                    return {"breakpoints": [], "toc": {}}
                continue

    if not toc_dict:
        return {"breakpoints": [], "toc": {}}

    # Find ToC boundary using either the last title's position, or the ToC region end.
    # When vision extraction is used, titles may come from images and not match OCR text exactly.
    last_title = max(toc_dict, key=lambda t: toc_dict[t])
    last_title_matches = [
        m.start() for m in re.finditer(re.escape(last_title), text)
    ]

    if last_title_matches:
        last_toc_title_index = last_title_matches[0]
    else:
        # Fallback: if the last title isn't found in text (e.g., due to OCR/image mismatch),
        # use the end of the ToC region as the boundary instead of returning 0.
        # This is common when vision extraction extracts titles from images.
        if toc_region is not None:
            last_toc_title_index = toc_region[1]
        else:
            return {"breakpoints": [], "toc": {}}

    # Step 4: Detect page-number pattern (now returns tuple or None)
    pattern_result = _detect_page_pattern(text, toc_dict, last_toc_title_index)
    page_pattern = pattern_result[0] if pattern_result else None
    numeral_type = pattern_result[1] if pattern_result else "arabic"

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
                text, target_page, page_pattern, last_toc_title_index,
                numeral_type=numeral_type,
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
    # Try exact match first, then fuzzy normalized match
    for title in title_fallback_titles:
        # Exact match
        matches = [
            m.start()
            for m in re.finditer(re.escape(title), text)
            if m.start() >= last_toc_title_index
        ]
        if matches:
            confirmed_indices[title] = matches[0]
            continue

        # Fuzzy normalized match (strips །, whitespace, newlines)
        fuzzy_pos = _fuzzy_find_title_in_text(text, title, last_toc_title_index)
        if fuzzy_pos is not None:
            confirmed_indices[title] = fuzzy_pos

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

    # Step 6: Refine each breakpoint to the actual title start position
    sorted_titles = sorted(confirmed_indices, key=lambda t: confirmed_indices[t])
    for i, title in enumerate(sorted_titles):
        if i + 1 < len(sorted_titles):
            next_bound = confirmed_indices[sorted_titles[i + 1]]
        else:
            next_bound = None
        refined = _refine_index_to_title(
            text, confirmed_indices[title], title, next_bound
        )
        confirmed_indices[title] = refined

    # Return sorted indices with TOC mapping
    return {
        "breakpoints": sorted(confirmed_indices.values()),
        "toc": toc_dict,
    }
