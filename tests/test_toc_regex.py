"""Tests for regex-based ToC extraction."""

import pytest

from ai_text_outline._toc_regex import extract_toc_regex, _tibetan_numeral_to_arabic


def test_extract_toc_regex_arabic_numerals():
    """Test extracting ToC with Arabic numerals in parentheses."""
    # Tibetan text with page numbers in parentheses (actual format from test.txt)
    text = """དཀར་ཆག
    པད་མ་འཆེར་གླེང (1)
    གངས་ཅན་གྱི་མདའ་ཡིག (5)
    དགེ་བའི་རིས་ཕུལ་བྱེད (10)
    """
    result = extract_toc_regex(text)
    assert result is not None
    assert len(result) > 0
    # Check that page numbers are correct
    pages = list(result.values())
    assert 1 in pages
    assert 5 in pages
    assert 10 in pages


def test_extract_toc_regex_no_entries():
    """Test when no ToC entries are found."""
    text = "This is just regular text with no ToC entries"
    result = extract_toc_regex(text)
    assert result is None


def test_tibetan_numeral_conversion():
    """Test converting Tibetan numerals to Arabic."""
    assert _tibetan_numeral_to_arabic("༠") == "0"
    assert _tibetan_numeral_to_arabic("༡༢༣") == "123"
    assert _tibetan_numeral_to_arabic("༩༩") == "99"
