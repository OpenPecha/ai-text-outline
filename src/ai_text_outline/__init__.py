"""
ai_text_outline: Extract Table of Contents from Tibetan texts.

Main public API:
  extract_toc_indices(file_path=None, text=None, ...) -> dict
    Returns: {"breakpoints": list[int], "toc": dict[str, int]}
"""

from ._extract import extract_toc_indices

__all__ = ["extract_toc_indices"]
__version__ = "0.8.0"
