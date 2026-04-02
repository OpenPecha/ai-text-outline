"""Tests for LLM module."""

import pytest

from ai_text_outline._llm import _parse_response, _parse_indices_response


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


# Tests for _parse_indices_response

def test_parse_indices_response_valid_json():
    """Test parsing valid indices JSON."""
    response = '{"indices": [100, 2000, 5000]}'
    result = _parse_indices_response(response)
    assert result == [100, 2000, 5000]


def test_parse_indices_response_with_markdown():
    """Test parsing indices JSON wrapped in markdown fences."""
    response = """```json
{"indices": [150, 3000, 7500]}
```"""
    result = _parse_indices_response(response)
    assert result == [150, 3000, 7500]


def test_parse_indices_response_empty_indices():
    """Test parsing response with empty indices."""
    response = '{"indices": []}'
    result = _parse_indices_response(response)
    assert result == []


def test_parse_indices_response_missing_key():
    """Test parsing when indices key is missing."""
    response = '{"data": [100, 200]}'
    result = _parse_indices_response(response)
    assert result == []


def test_parse_indices_response_invalid_json():
    """Test parsing invalid JSON."""
    response = "This is not JSON"
    result = _parse_indices_response(response)
    assert result == []


def test_parse_indices_response_non_int_values():
    """Test parsing when indices contain non-integer values."""
    response = '{"indices": [100, "not an int", 5000]}'
    result = _parse_indices_response(response)
    # Should handle the error gracefully
    assert isinstance(result, list)
