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


# Tests for context length handling

def test_context_error_retries_with_smaller_slice(monkeypatch):
    """Test that context error on 1/5 triggers retry with 1/10."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Create a large text with chapter titles included
    large_text = (
        "Some intro text.\n"
        "Chapter 1\n"
        "Chapter 2\n"
        + ("x" * 10000) +
        "\nChapter 1 starts here\nContent\nChapter 2 starts here\nMore content"
    )

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        # First call (1/5) raises context error, second call (1/10) succeeds
        mock_gemini1.side_effect = [
            ValueError("Context length exceeded: Input too long"),
            {"Chapter 1": 1, "Chapter 2": 2}
        ]
        mock_gemini2.return_value = [100, 200]

        result = extract_toc_indices(text=large_text)

        # Should succeed with fallback
        assert result == [100, 200]
        # Should have been called twice
        assert mock_gemini1.call_count == 2


def test_context_error_cascades_through_fractions(monkeypatch):
    """Test that context errors cascade through 1/5 → 1/10 → 1/100."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    large_text = (
        "Some intro text.\n"
        "Chapter X\n"
        "Chapter Y\n"
        + ("y" * 20000) +
        "\nChapter X starts here\nContent\nChapter Y starts here\nMore"
    )

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        # First call (1/5) and second call (1/10) fail, third call (1/100) succeeds
        mock_gemini1.side_effect = [
            ValueError("Context length exceeded: Input too long (1/5)"),
            ValueError("Context length exceeded: Input too long (1/10)"),
            {"Chapter X": 1, "Chapter Y": 2}
        ]
        mock_gemini2.return_value = [150, 250]

        result = extract_toc_indices(text=large_text)

        # Should succeed with final fallback (1/100)
        assert result == [150, 250]
        # Should have been called 3 times (5, 10, 100)
        assert mock_gemini1.call_count == 3


def test_context_error_exhausts_all_fractions(monkeypatch):
    """Test that all fractions exhausted returns empty list."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = "Some text to extract"

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1:
        # All attempts fail
        mock_gemini1.side_effect = ValueError(
            "Context length exceeded: Even 1/100 is too long"
        )

        result = extract_toc_indices(text=text)

        # Should return empty list when all attempts fail
        assert result == []
        # Should have tried 3 times (5, 10, 100)
        assert mock_gemini1.call_count == 3


def test_success_on_first_fraction_stops_retrying(monkeypatch):
    """Test that successful first call (1/5) doesn't retry."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = "Some text.\nChapter 1\nChapter 2\nChapter 1 real\nChapter 2 real"

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        mock_gemini1.return_value = {"Chapter 1": 1, "Chapter 2": 2}
        mock_gemini2.return_value = [50, 100]

        result = extract_toc_indices(text=text)

        # Should succeed
        assert result == [50, 100]
        # Should only be called once (no retries needed)
        assert mock_gemini1.call_count == 1


def test_non_context_error_is_raised(monkeypatch):
    """Test that non-context errors are not caught and retried."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = "Some text"

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1:
        # Raise a different error (not context-related)
        mock_gemini1.side_effect = RuntimeError("API connection failed")

        with pytest.raises(RuntimeError, match="API connection failed"):
            extract_toc_indices(text=text)

        # Should only be called once (no retry for non-context errors)
        assert mock_gemini1.call_count == 1
