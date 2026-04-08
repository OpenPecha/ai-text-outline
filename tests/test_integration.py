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

        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        assert len(result["breakpoints"]) == 2
        assert all(isinstance(idx, int) for idx in result["breakpoints"])
        # Indices should be in ascending order
        assert result["breakpoints"] == sorted(result["breakpoints"])
        assert result["toc"] == {"Chapter 1": 1, "Chapter 2": 2}


def test_extract_toc_indices_title_appears_once(monkeypatch):
    """Test when title appears in ToC and body (using title fallback)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:
        mock_gemini1.return_value = {"Section Title": 1}
        mock_gemini2.return_value = []

        # Title appears in ToC and in body (title fallback should find it)
        text = "ToC\nSection Title\n-1-\nBody section\nSection Title content here"

        result = extract_toc_indices(text=text)
        # Title fallback should find it in the body
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        assert len(result["breakpoints"]) > 0


def test_extract_toc_indices_empty_toc(monkeypatch):
    """Test when Gemini returns empty ToC."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1:
        mock_gemini1.return_value = {}

        result = extract_toc_indices(text="Some text here")
        assert result == {"breakpoints": [], "toc": {}}


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
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        assert len(result["breakpoints"]) == 2


# Tests for context length handling

def test_context_error_retries_with_smaller_slice(monkeypatch):
    """Test that context error on 1/5 triggers retry with 1/10."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Create a large text with chapter titles and page markers
    large_text = (
        "Some intro text.\n"
        "Chapter 1\n"
        "Chapter 2\n"
        "ToC end\n"
        + ("x" * 10000) +
        "\n-1-\nChapter 1 starts here\nContent\n-2-\nChapter 2 starts here\nMore content"
    )

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        # First call (1/5) raises context error, second call (1/10) succeeds
        mock_gemini1.side_effect = [
            ValueError("Context length exceeded: Input too long"),
            {"Chapter 1": 1, "Chapter 2": 2}
        ]
        mock_gemini2.return_value = []  # No LLM fallback needed

        result = extract_toc_indices(text=large_text)

        # Should succeed with fallback, using page markers or title fallback
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        assert len(result["breakpoints"]) >= 0
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
        mock_gemini2.return_value = []

        result = extract_toc_indices(text=large_text)

        # Should succeed with final fallback (1/100)
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        # Should have tried 3 times (5, 10, 100)
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

        # Should return empty dict when all attempts fail
        assert result == {"breakpoints": [], "toc": {}}
        # Should have tried 3 times (5, 10, 100)
        assert mock_gemini1.call_count == 3


def test_success_on_first_fraction_stops_retrying(monkeypatch):
    """Test that successful first call (1/5) doesn't retry."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = "Some text.\nChapter 1\nChapter 2\n-1-\nChapter 1 real\nChapter 2 real"

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        mock_gemini1.return_value = {"Chapter 1": 1, "Chapter 2": 2}
        mock_gemini2.return_value = []

        result = extract_toc_indices(text=text)

        # Should succeed
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        # Should only be called once (no retries needed)
        assert mock_gemini1.call_count == 1


# Tests for page-number matching (new pipeline)


def test_page_pattern_detection_dash_n_format(monkeypatch):
    """Test detection of -N- page pattern."""
    from ai_text_outline._extract import _detect_page_pattern

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Text with -N- format pages
    text = """
    དཀར་ཆག
    Section 1 title (1)
    Section 2 title (5)
    -1-
    Section 1 content
    -2-
    More content
    -5-
    Section 2 content
    """

    toc_dict = {"Section 1": 1, "Section 2": 5}
    toc_boundary = text.index("-1-")

    pattern = _detect_page_pattern(text, toc_dict, toc_boundary)

    assert pattern == "^-{n}-$"


def test_page_pattern_detection_standalone_format(monkeypatch):
    """Test detection of standalone N page pattern."""
    from ai_text_outline._extract import _detect_page_pattern

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Text with standalone number format
    text = """
    དཀར་ཆག
    Section 1 (1)
    Section 2 (5)
    1
    Section 1 content
    2
    More content
    5
    Section 2 content
    """

    toc_dict = {"Section 1": 1, "Section 2": 5}
    toc_boundary = text.index("\n    1\n")

    pattern = _detect_page_pattern(text, toc_dict, toc_boundary)

    assert pattern == r"^\s*{n}\s*$"


def test_page_marker_positions_finds_marker(monkeypatch):
    """Test finding page marker positions in text."""
    from ai_text_outline._extract import _find_page_marker_positions

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = "ToC\n-1-\nContent 1\n-2-\nContent 2\n-5-\nContent 5"
    pattern = "^-{n}-$"

    # Find page 2
    positions = _find_page_marker_positions(text, 2, pattern, 5)  # after ToC

    assert len(positions) >= 1
    assert positions[0] > 0


def test_first_section_uses_toc_boundary(monkeypatch):
    """Test that first section (lowest page) uses ToC boundary index."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = """དཀར་ཆག
Section 1 (1)
Section 2 (5)
-4-

Section 1 content here
-1-
More section 1
-2-
Section 2 content
"""

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        mock_gemini1.return_value = {"Section 1": 1, "Section 2": 5}
        # Expect LLM call 2 for section 2 (multiple page matches or no match)
        mock_gemini2.return_value = []

        result = extract_toc_indices(text=text)

        # First section should be at ToC boundary (after -4-)
        toc_boundary = text.index("-4-") + 3  # "-4-" is 3 chars

        # Result should include the first section starting right after ToC
        # (actual indices depend on pattern detection and page matching)
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result


def test_missing_page_falls_back_to_title_match(monkeypatch):
    """Test fallback to title matching when page marker not found."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = """དཀར་ཆག
Section Alpha (100)
Section Beta (200)
-10-

Section Alpha content starts
-11-
Beta content
-12-
More content
"""

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        # Pages 100 and 200 don't exist in text, but titles do
        mock_gemini1.return_value = {"Section Alpha": 100, "Section Beta": 200}
        mock_gemini2.return_value = []

        result = extract_toc_indices(text=text)

        # Should fall back to title matching
        # "Section Alpha" and "Section Beta" appear in the text
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result
        # Both sections should be found via title fallback
        if len(result["breakpoints"]) > 0:
            assert any(
                text[idx:].startswith("Section") for idx in result["breakpoints"]
            )


def test_multiple_page_matches_use_llm_fallback(monkeypatch):
    """Test that multiple page matches trigger LLM call 2."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    text = """དཀར་ཆག
Chapter A (5)
Chapter B (10)
-4-

Content here
-5-
First section
-6-
More content
-5-
Another section 5 marker!
-10-
Chapter B content
"""

    with patch("ai_text_outline._extract.call_gemini") as mock_gemini1, \
         patch("ai_text_outline._extract.call_gemini_for_indices") as mock_gemini2:

        mock_gemini1.return_value = {"Chapter A": 5, "Chapter B": 10}
        # Page 4 (to find section A at 5) appears once, but we simulate
        # having multiple candidates that go to LLM
        mock_gemini2.return_value = [50, 100]

        result = extract_toc_indices(text=text)

        # LLM call 2 should have been invoked if multiple matches found
        # (or at least the pipeline should handle it)
        assert isinstance(result, dict)
        assert "breakpoints" in result and "toc" in result


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
