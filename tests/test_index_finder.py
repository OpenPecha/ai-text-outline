"""Tests for finding section indices."""

import pytest

from ai_text_outline._config import Config, Provider
from ai_text_outline._index_finder import find_section_indices, _find_by_page_marker


def test_find_section_indices_with_page_markers():
    """Test finding sections when page markers exist."""
    text = "Intro text [1] First chapter content here [2] Second chapter content"
    toc = {
        "First chapter": 1,
        "Second chapter": 2,
    }
    config = Config(
        provider=Provider.GEMINI,
        model="test",
        api_key="test",
        chars_per_page=2000,
        fuzzy_threshold=0.9,
    )

    indices = find_section_indices(toc, text, config)
    assert len(indices) > 0
    assert all(isinstance(i, int) for i in indices)


def test_find_by_page_marker():
    """Test finding a page marker."""
    text = "Some intro [1] Page one content [2] Page two content"
    page_markers = [(1, text.find("[1]")), (2, text.find("[2]"))]

    idx = _find_by_page_marker(1, text, page_markers)
    assert idx is not None
    assert idx > text.find("[1]")  # Should be after the marker


def test_find_by_page_marker_not_found():
    """Test when page marker doesn't exist."""
    text = "Some text [1] content"
    page_markers = [(1, text.find("[1]"))]

    idx = _find_by_page_marker(999, text, page_markers)
    assert idx is None


def test_find_section_indices_empty_toc():
    """Test with empty ToC."""
    text = "Some text content"
    toc = {}
    config = Config(
        provider=Provider.GEMINI,
        model="test",
        api_key="test",
    )

    indices = find_section_indices(toc, text, config)
    assert indices == []
