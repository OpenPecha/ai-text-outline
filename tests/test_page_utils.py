"""Tests for page utilities."""

import pytest

from ai_text_outline._page_utils import (
    estimate_total_pages,
    get_toc_slice,
    find_page_markers,
    find_toc_section,
)


def test_estimate_total_pages():
    """Test page estimation."""
    text_1000 = "x" * 1000
    assert estimate_total_pages(text_1000, 2000) == 1  # Less than 1 page rounds to 1

    text_4000 = "x" * 4000
    assert estimate_total_pages(text_4000, 2000) == 2

    text_5000 = "x" * 5000
    assert estimate_total_pages(text_5000, 2000) == 2


def test_get_toc_slice_small_text():
    """Test ToC slice for small text."""
    text = "x" * 1000 * 500  # 500 pages
    slice_result = get_toc_slice(text, chars_per_page=2000)
    # First quarter: 500/4 = 125 pages
    expected_len = len(text) // 4
    assert len(slice_result) == expected_len


def test_get_toc_slice_large_text():
    """Test ToC slice for large text (>= 1000 pages)."""
    text = "x" * 2000 * 1200  # 1200 pages
    slice_result = get_toc_slice(text, chars_per_page=2000)
    # First 100 pages
    expected_len = 100 * 2000
    assert len(slice_result) == expected_len


def test_find_page_markers():
    """Test finding page markers."""
    text = "Some text [1] more text (2) even more [3]"
    markers = find_page_markers(text)
    assert len(markers) == 3
    # Check that markers are in order and have correct page numbers
    page_nums = [p for p, _ in markers]
    assert page_nums == [1, 2, 3]


def test_find_page_markers_various_formats():
    """Test various page marker formats."""
    text = "Page [1] and (2) and 【3】 and {4}"
    markers = find_page_markers(text)
    assert len(markers) >= 3  # At least bracket, paren, and CJK bracket formats


def test_find_toc_section_with_marker():
    """Test finding ToC section with དཀར་ཆག marker."""
    text = "Some introduction\nདཀར་ཆག\nChapter 1\npage 1\nདཀར་ཆག\nMore content\n\nNext section"
    result = find_toc_section(text, chars_per_page=100)
    assert result is not None
    assert "Chapter" in result or "page" in result


def test_find_toc_section_no_marker():
    """Test when དཀར་ཆག is not found."""
    text = "This is some text without any ToC marker"
    result = find_toc_section(text, chars_per_page=100)
    assert result is None
