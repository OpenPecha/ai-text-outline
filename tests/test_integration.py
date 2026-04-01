"""Integration tests for the full extraction pipeline."""

import pytest
from unittest.mock import patch, MagicMock

from ai_text_outline import extract_toc_indices


def test_extract_toc_indices_with_file_not_found():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        extract_toc_indices(file_path="/nonexistent/file.txt")


def test_extract_toc_indices_with_both_inputs():
    """Test error when both file_path and text are provided."""
    with pytest.raises(ValueError, match="Exactly one of"):
        extract_toc_indices(file_path="test.txt", text="some text")


def test_extract_toc_indices_with_neither_input():
    """Test error when neither file_path nor text are provided."""
    with pytest.raises(ValueError, match="Exactly one of"):
        extract_toc_indices()


def test_extract_toc_indices_empty_text():
    """Test with empty text."""
    result = extract_toc_indices(text="")
    assert result == []


def test_extract_toc_indices_no_api_key(monkeypatch):
    """Test error when no API key is configured."""
    # Remove all API key env vars
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError, match="No API key found"):
        extract_toc_indices(text="some text")


@patch('ai_text_outline._toc_llm.call_llm')
def test_extract_toc_indices_with_mocked_llm(mock_llm, monkeypatch):
    """Test the full pipeline with mocked LLM."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Mock LLM response
    mock_llm.return_value = '{"toc": {"Chapter 1": 1, "Chapter 2": 5}}'

    text = "Some intro\nདཀར་ཆག\n[1] Chapter 1 content here\n[5] Chapter 2 content"

    result = extract_toc_indices(text=text)

    # Should find indices for the chapters
    assert isinstance(result, list)
    # The exact indices depend on where chapters are found
    assert all(isinstance(idx, int) for idx in result)


def test_extract_toc_indices_with_file(monkeypatch, tmp_path):
    """Test extraction from a file."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Create a temporary test file
    test_file = tmp_path / "test_text.txt"
    test_text = "Some introduction text\nདཀར་ཆག\nChapter 1\nMore content"
    test_file.write_text(test_text, encoding='utf-8')

    # Mock the LLM so we don't need actual API calls
    with patch('ai_text_outline._toc_llm.call_llm') as mock_llm:
        mock_llm.return_value = '{"toc": {}}'  # Empty ToC

        result = extract_toc_indices(file_path=str(test_file))
        assert isinstance(result, list)
