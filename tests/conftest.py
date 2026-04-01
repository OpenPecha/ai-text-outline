"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_text():
    """Sample Tibetan text for testing."""
    return """Some intro text about the book.

དཀར་ཆག
Chapter 1 Content
Chapter 2 Content
Chapter 3 Content

Chapter 1 Content - Full section starts here
Lorem ipsum dolor sit amet
...
Chapter 2 Content - Second section
More content about chapter 2
...
Chapter 3 Content - Third section
Even more content
"""
