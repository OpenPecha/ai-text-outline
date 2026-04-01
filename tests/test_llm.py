"""Tests for LLM module."""

import pytest

from ai_text_outline._llm import _parse_response


def test_parse_response_valid_json():
    """Test parsing valid JSON response."""
    response = '{"toc": {"Chapter 1": 1, "Chapter 2": 5}}'
    result = _parse_response(response)
    assert result == {"Chapter 1": 1, "Chapter 2": 5}


def test_parse_response_with_markdown_fences():
    """Test parsing JSON wrapped in markdown code fences."""
    response = """```json
{"toc": {"Title A": 10, "Title B": 20}}
```"""
    result = _parse_response(response)
    assert result == {"Title A": 10, "Title B": 20}


def test_parse_response_empty_toc():
    """Test parsing response with empty ToC."""
    response = '{"toc": {}}'
    result = _parse_response(response)
    assert result == {}


def test_parse_response_missing_toc_key():
    """Test parsing when toc key is missing."""
    response = '{"data": {"Chapter": 1}}'
    result = _parse_response(response)
    assert result == {}


def test_parse_response_invalid_json():
    """Test parsing invalid JSON."""
    response = "This is not JSON at all"
    result = _parse_response(response)
    assert result == {}


def test_parse_response_with_extra_text():
    """Test parsing JSON with surrounding text."""
    response = "Here is the ToC: {\"toc\": {\"Ch1\": 5}} Thank you!"
    result = _parse_response(response)
    assert result == {"Ch1": 5}
