"""Integration tests for the full extraction pipeline."""

import pytest
from unittest.mock import patch

from ai_text_outline import extract_toc_indices


def test_extract_toc_indices_with_file_not_found():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        extract_toc_indices(file_path="/nonexistent/file.txt")


def test_extract_toc_indices_with_both_inputs():
    """Test error when both file_path and text are provided."""
    with pytest.raises(ValueError, match="Provide exactly one"):
        extract_toc_indices(file_path="test.txt", text="some text")


def test_extract_toc_indices_with_neither_input():
    """Test error when neither file_path nor text are provided."""
    with pytest.raises(ValueError, match="Provide exactly one"):
        extract_toc_indices()


def test_extract_toc_indices_no_api_key(monkeypatch):
    """Test error when no API key is configured."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="No Gemini API key"):
        extract_toc_indices(text="some text")


def test_extract_toc_indices_with_mocked_gemini(monkeypatch):
    """Test the full pipeline with mocked Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Mock both Gemini calls
    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        mock_gemini1.return_value = {"Chapter 1": 1, "Chapter 2": 2}
        mock_gemini2.return_value = [50, 100]  # Indices for Chapter 1 and Chapter 2

        text = "Some intro text.\nChapter 1\nChapter 2\nReal Chapter 1 starts here\nContent for chapter 1.\nReal Chapter 2 starts here\nContent for chapter 2."

        result = extract_toc_indices(text=text)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(idx, int) for idx in result)
        # Indices should be in ascending order
        assert result == sorted(result)


def test_extract_toc_indices_title_appears_once(monkeypatch):
    """Test when title appears only once (in ToC section)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:
        mock_gemini1.return_value = {"Unique Title": 1}
        mock_gemini2.return_value = []  # No valid indices found

        text = "Some intro.\nUnique Title\nSome other content."

        result = extract_toc_indices(text=text)
        # Title appears only once, so Gemini returns empty list
        assert result == []


def test_extract_toc_indices_empty_toc(monkeypatch):
    """Test when Gemini returns empty ToC."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1:
        mock_gemini1.return_value = {}

        result = extract_toc_indices(text="Some text here")
        assert result == []


def test_extract_toc_indices_with_file(monkeypatch, tmp_path):
    """Test extraction from a file."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    test_file = tmp_path / "test.txt"
    test_text = "Introduction.\nChapter A\nChapter B\nChapter A starts here\nContent A.\nChapter B starts here\nContent B."
    test_file.write_text(test_text, encoding="utf-8")

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:
        mock_gemini1.return_value = {"Chapter A": 1, "Chapter B": 2}
        mock_gemini2.return_value = [60, 100]  # Returned indices

        result = extract_toc_indices(file_path=str(test_file))
        assert isinstance(result, list)
        assert len(result) == 2
