"""Configuration and provider resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os


class Provider(Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"


@dataclass
class Config:
    """Configuration for ToC extraction."""
    provider: Provider
    model: str
    api_key: str
    chars_per_page: int = 2000
    fuzzy_threshold: float = 0.9


def resolve_config(
    provider: str | None,
    model: str | None,
    chars_per_page: int,
    fuzzy_threshold: float,
) -> Config:
    """
    Resolve configuration from parameters and environment variables.

    Priority order for provider: GEMINI > OPENAI > CLAUDE

    Args:
        provider: Optional provider name ("gemini", "openai", "claude")
        model: Optional model name
        chars_per_page: Characters per page for estimation
        fuzzy_threshold: Fuzzy match threshold (0.0-1.0)

    Returns:
        Resolved Config object

    Raises:
        ValueError: If no API key found for any provider
    """
    # Default models per provider
    default_models = {
        "gemini": "gemini-2.0-flash",
        "openai": "gpt-4o",
        "claude": "claude-sonnet-4-20250514",
    }

    # If provider is specified, use it
    if provider:
        provider_lower = provider.lower()
        if provider_lower not in default_models:
            raise ValueError(f"Unknown provider: {provider}. Must be one of: gemini, openai, claude")

        api_key_var = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }[provider_lower]

        api_key = os.getenv(api_key_var)
        if not api_key:
            raise ValueError(f"API key not found. Set the {api_key_var} environment variable.")

        chosen_provider = Provider[provider_lower.upper()]
        chosen_model = model or default_models[provider_lower]
        return Config(
            provider=chosen_provider,
            model=chosen_model,
            api_key=api_key,
            chars_per_page=chars_per_page,
            fuzzy_threshold=fuzzy_threshold,
        )

    # Auto-detect provider by checking env vars in priority order
    for prov_name in ["gemini", "openai", "claude"]:
        api_key_var = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }[prov_name]

        api_key = os.getenv(api_key_var)
        if api_key:
            chosen_provider = Provider[prov_name.upper()]
            chosen_model = model or default_models[prov_name]
            return Config(
                provider=chosen_provider,
                model=chosen_model,
                api_key=api_key,
                chars_per_page=chars_per_page,
                fuzzy_threshold=fuzzy_threshold,
            )

    raise ValueError(
        "No API key found. Set one of: GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
    )
