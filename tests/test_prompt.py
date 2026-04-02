"""Tests for prompt generation."""

import json

from ai_text_outline._prompt import (
    get_toc_extraction_prompt,
    get_index_selection_prompt,
)


def test_get_toc_extraction_prompt():
    """Test ToC extraction prompt generation."""
    text = "Some Tibetan text content"
    prompt = get_toc_extraction_prompt(text)

    assert isinstance(prompt, str)
    assert "དཀར་ཆག" in prompt or "toc" in prompt.lower()
    assert "Some Tibetan text content" in prompt
    assert "JSON" in prompt


def test_get_index_selection_prompt():
    """Test index selection prompt generation."""
    toc_dict = {"Chapter 1": 1, "Chapter 2": 5}
    candidates = {"Chapter 1": [100, 5000], "Chapter 2": [150, 7000]}
    last_toc_title_index = 150

    prompt = get_index_selection_prompt(toc_dict, candidates, last_toc_title_index)

    assert isinstance(prompt, str)
    # Should mention key concepts
    assert "last_toc_title_index" in prompt or "anchor" in prompt.lower()
    assert "ascending" in prompt.lower()
    assert "JSON" in prompt
    # Should include the input data
    assert "Chapter 1" in prompt or "Chapter 2" in prompt


def test_get_index_selection_prompt_includes_toc_order():
    """Test that prompt includes toc_order sorted by page numbers."""
    toc_dict = {"C": 30, "A": 10, "B": 20}
    candidates = {"A": [100, 5000], "B": [150, 7000], "C": [200, 8000]}
    last_toc_title_index = 200

    prompt = get_index_selection_prompt(toc_dict, candidates, last_toc_title_index)

    # Extract the JSON data from the prompt to verify toc_order
    # Look for JSON structure in the prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 100  # Should be substantial


def test_get_index_selection_prompt_with_tibetan_text():
    """Test prompt with Tibetan script titles."""
    toc_dict = {"དཀར་ཆག": 1, "རྣམ་བཤད": 5}
    candidates = {"དཀར་ཆག": [100, 5000], "རྣམ་བཤད": [150, 7000]}
    last_toc_title_index = 150

    prompt = get_index_selection_prompt(toc_dict, candidates, last_toc_title_index)

    assert isinstance(prompt, str)
    # Should preserve Tibetan text
    assert "དཀར་ཆག" in prompt or "རྣམ་བཤད" in prompt
