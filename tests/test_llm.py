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


# Tests for context error handling in call_gemini


def test_call_gemini_context_error_handling(monkeypatch):
    """Test that call_gemini raises ValueError on context length errors."""
    from ai_text_outline._llm import call_gemini
    from unittest.mock import MagicMock, patch
    import sys

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Mock the genai module before it's imported in call_gemini
    mock_genai = MagicMock()
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client

    # Simulate context length error
    mock_client.models.generate_content.side_effect = Exception(
        "Request failed with status code 400: Request body is too large"
    )

    with patch.dict(sys.modules, {"google.genai": mock_genai}):
        with pytest.raises(ValueError, match="Context length exceeded"):
            call_gemini("some prompt", "test-key")


def test_call_gemini_token_quota_error_handling(monkeypatch):
    """Test that call_gemini raises ValueError on token quota errors."""
    from ai_text_outline._llm import call_gemini
    from unittest.mock import MagicMock, patch
    import sys

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_genai = MagicMock()
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client

    # Simulate quota error
    mock_client.models.generate_content.side_effect = Exception(
        "Quota exceeded for quota metric 'tokens' and 'token-per-min-per-user'"
    )

    with patch.dict(sys.modules, {"google.genai": mock_genai}):
        with pytest.raises(ValueError, match="Context length exceeded"):
            call_gemini("some prompt", "test-key")


def test_call_gemini_other_errors_not_caught(monkeypatch):
    """Test that call_gemini re-raises non-context errors."""
    from ai_text_outline._llm import call_gemini
    from unittest.mock import MagicMock, patch
    import sys

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_genai = MagicMock()
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client

    # Simulate a different error (not context-related)
    mock_client.models.generate_content.side_effect = RuntimeError("API connection failed")

    with patch.dict(sys.modules, {"google.genai": mock_genai}):
        # Should re-raise the original error
        with pytest.raises(RuntimeError, match="API connection failed"):
            call_gemini("some prompt", "test-key")
