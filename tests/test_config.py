"""Tests for configuration and provider resolution."""

import os
import pytest

from ai_text_outline._config import Config, Provider, resolve_config


def test_resolve_config_explicit_provider(monkeypatch):
    """Test resolving config with explicit provider."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")

    config = resolve_config(
        provider="gemini",
        model=None,
        chars_per_page=2000,
        fuzzy_threshold=0.9,
    )

    assert config.provider == Provider.GEMINI
    assert config.model == "gemini-2.0-flash"
    assert config.api_key == "test-key-123"


def test_resolve_config_auto_detect(monkeypatch):
    """Test auto-detecting provider from env vars."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    config = resolve_config(
        provider=None,
        model=None,
        chars_per_page=2000,
        fuzzy_threshold=0.9,
    )

    assert config.provider == Provider.OPENAI
    assert config.model == "gpt-4o"


def test_resolve_config_no_key(monkeypatch):
    """Test error when no API key is found."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError, match="No API key found"):
        resolve_config(
            provider=None,
            model=None,
            chars_per_page=2000,
            fuzzy_threshold=0.9,
        )


def test_resolve_config_custom_model(monkeypatch):
    """Test custom model name."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    config = resolve_config(
        provider="gemini",
        model="gemini-1.5-pro",
        chars_per_page=2500,
        fuzzy_threshold=0.85,
    )

    assert config.model == "gemini-1.5-pro"
    assert config.chars_per_page == 2500
    assert config.fuzzy_threshold == 0.85
