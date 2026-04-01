"""Main extraction pipeline."""

from __future__ import annotations

import logging

from ._config import resolve_config
from ._index_finder import find_section_indices
from ._page_utils import find_toc_section, get_toc_slice
from ._toc_llm import extract_toc_llm
from ._toc_regex import extract_toc_regex

logger = logging.getLogger(__name__)


def extract_toc_indices(
    file_path: str | None = None,
    text: str | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    chars_per_page: int = 2000,
    fuzzy_threshold: float = 0.9,
) -> list[int]:
    """
    Extract Table of Contents from Tibetan text and return section start indices.

    Pipeline:
      1. Validate and load input text
      2. Extract ToC section using དཀར་ཆག markers (or fallback)
      3. Parse ToC entries via regex (or LLM if regex fails)
      4. Find character indices of each ToC entry in full text
      5. Return sorted list of indices

    Args:
        file_path: Path to text file (mutually exclusive with text)
        text: Text content string (mutually exclusive with file_path)
        provider: LLM provider ("gemini", "openai", "claude"). Auto-detected if None
        model: LLM model name. Uses provider defaults if None
        chars_per_page: Estimated characters per page (default 2000)
        fuzzy_threshold: Fuzzy match threshold for title finding (0.0-1.0, default 0.9)

    Returns:
        Sorted list of character indices where each ToC section starts.
        Returns empty list if no ToC found.

    Raises:
        ValueError: If both/neither file_path and text provided, or no API key found
        FileNotFoundError: If file_path doesn't exist
        UnicodeDecodeError: If file encoding is not UTF-8
    """
    # Step 1: Validate and load text
    if (file_path is None and text is None) or (file_path is not None and text is not None):
        raise ValueError("Exactly one of file_path or text must be provided")

    if file_path:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    else:
        full_text = text

    if not full_text:
        logger.warning("Input text is empty")
        return []

    logger.info(f"Loaded text: {len(full_text)} characters")

    # Step 2: Resolve configuration
    config = resolve_config(provider, model, chars_per_page, fuzzy_threshold)
    logger.debug(f"Using provider: {config.provider.value}, model: {config.model}")

    # Step 3: Extract ToC section
    toc_section = find_toc_section(full_text, chars_per_page)

    if toc_section:
        logger.info(f"Found དཀར་ཆག section: {len(toc_section)} characters")
    else:
        logger.info("དཀར་ཆག section not found, using fallback slice")
        toc_section = get_toc_slice(full_text, chars_per_page)

    # Step 4: Parse ToC entries
    toc_dict = extract_toc_regex(toc_section)

    if not toc_dict:
        logger.info("Regex ToC extraction failed, attempting LLM extraction")
        toc_dict = extract_toc_llm(toc_section, config)

    if not toc_dict:
        logger.warning("No ToC entries extracted")
        return []

    logger.info(f"Extracted {len(toc_dict)} ToC entries")
    for title, page in list(toc_dict.items())[:5]:  # Log first 5
        logger.debug(f"  - {title}: page {page}")

    # Step 5: Find section indices
    indices = find_section_indices(toc_dict, full_text, config)
    logger.info(f"Located {len(indices)} section starts")

    return indices
