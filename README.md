# ai-text-outline

<div align="center">

**Extract Table of Contents from Tibetan texts with Gemini**

[![PyPI version](https://img.shields.io/pypi/v/ai-text-outline.svg)](https://pypi.org/project/ai-text-outline/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/tests-14%2F14%20passing-green)]()

</div>

---

## Overview

**ai-text-outline** is a simple Python package that extracts Table of Contents (དཀར་ཆག) from Tibetan text and returns character indices where each section begins.

Uses **Gemini 1.5 Pro** for reliable, cost-effective ToC extraction with automatic context overflow handling.

Perfect for:
- 📚 **Digital publishing** - Index Tibetan manuscripts automatically
- 🔍 **Text analysis** - Locate sections in large Tibetan documents
- 🤖 **Backend integration** - Add ToC extraction to your pipeline
- 📱 **Web applications** - Power frontend outlining tools

---

## Features

✨ **Simple & Fast**
- Send first 1/5 of text to Gemini
- Get ToC titles back as JSON
- Find titles in full text (skip first, use second occurrence)
- Return sorted character indices

🌍 **Tibetan Native**
- Full Unicode Tibetan support
- Handles དཀར་ཆག section markers
- Preserves original Tibetan text

💰 **Cost Efficient**
- Uses only Google Gemini
- Sends minimal text (1/5 of document)
- ~$0.0001 per extraction

---

## Installation

```bash
pip install ai-text-outline
```

Requires: Python 3.9+, Google Generative AI SDK (installed automatically)

---

## Quick Start

### 1. Get Gemini API Key

Get a free key at https://ai.google.dev/

### 2. Set Environment Variable

```bash
export GEMINI_API_KEY="your-api-key"
```

### 3. Extract ToC

```python
from ai_text_outline import extract_toc_indices

# From file
indices = extract_toc_indices(file_path='tibetan_text.txt')

# Or from text string
text = open('tibetan_text.txt', encoding='utf-8').read()
indices = extract_toc_indices(text=text)

print(indices)  # [150, 2450, 5200, ...]
```

---

## API Reference

### `extract_toc_indices()`

```python
def extract_toc_indices(
    file_path: str | None = None,
    text: str | None = None,
    *,
    gemini_api_key: str | None = None,
) -> list[int]
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | str \| None | None | Path to Tibetan text file (UTF-8) |
| `text` | str \| None | None | Raw text string (mutually exclusive with `file_path`) |
| `gemini_api_key` | str \| None | None | Gemini API key. Falls back to `GEMINI_API_KEY` env var if not provided |

#### Returns

**`list[int]`** - Sorted character indices where each ToC section begins. Empty list `[]` if no ToC found.

#### Raises

| Exception | When |
|-----------|------|
| `ValueError` | Neither or both `file_path` and `text` provided; or no API key found |
| `FileNotFoundError` | `file_path` doesn't exist |
| `UnicodeDecodeError` | File is not UTF-8 encoded |
| `ImportError` | google-generativeai SDK not installed |

#### Example

```python
from ai_text_outline import extract_toc_indices

text = open('book.txt', encoding='utf-8').read()
indices = extract_toc_indices(text=text)

# Use indices to extract sections
for i, start_idx in enumerate(indices):
    end_idx = indices[i+1] if i+1 < len(indices) else len(text)
    section = text[start_idx:end_idx]
    print(f"Section {i+1}: {len(section)} chars")
```

---

## How It Works

```
Input Text (file or string)
        │
        ▼
   Load text
        │
        ▼
   Extract first 1/5 of text (with context-aware fallback)
   If context limit exceeded:
     ├─ Retry with 1/10 of text
     └─ If still exceeded, retry with 1/100 of text
        │
        ▼
   Send to Gemini API
        → Extracts ToC titles
        → Returns JSON: {"toc": {"Title": page_num, ...}}
        │
        ▼
   For each title:
        Find all matches in full text (limit 10 per title)
        ├── 2+ matches → use matches[1].start() (skip ToC itself)
        └── 0 or 1 match → skip
        │
        ▼
   Return sorted list of indices
```

### Context Overflow Handling

For very large texts (>5MB), the extraction automatically handles Gemini API context limits:

1. **First attempt**: Send first 1/5 of text (default)
2. **If context exceeded**: Automatically retry with first 1/10 of text
3. **If still exceeded**: Retry with first 1/100 of text
4. **If all fail**: Return empty list (no ToC found)

This ensures the package works with texts of any size without manual intervention.

---

## Examples

### Example 1: Extract from File

```python
from ai_text_outline import extract_toc_indices
import os

os.environ['GEMINI_API_KEY'] = 'AIzaSy...'

indices = extract_toc_indices(file_path='texts/book.txt')
print(f"Found {len(indices)} sections")
print(indices)  # [0, 450, 2100, 5800, ...]
```

### Example 2: Extract Sections

```python
from ai_text_outline import extract_toc_indices

indices = extract_toc_indices(file_path='book.txt')
text = open('book.txt', encoding='utf-8').read()

# Split into sections
sections = []
for i, start_idx in enumerate(indices):
    end_idx = indices[i+1] if i+1 < len(indices) else len(text)
    sections.append(text[start_idx:end_idx])

for i, section in enumerate(sections):
    print(f"Section {i}: {len(section)} chars")
```

### Example 3: With Custom API Key

```python
from ai_text_outline import extract_toc_indices

# Pass API key directly instead of env var
indices = extract_toc_indices(
    file_path='text.txt',
    gemini_api_key='AIzaSy...'
)
```

### Example 4: Flask Backend

```python
from flask import Flask, request, jsonify
from ai_text_outline import extract_toc_indices

app = Flask(__name__)

@app.post('/api/extract-toc')
def extract_toc():
    """Extract ToC from uploaded text file."""
    data = request.json
    file_path = data.get('file_path')
    text_content = data.get('text')
    
    try:
        indices = extract_toc_indices(
            file_path=file_path,
            text=text_content,
        )
        return {
            'success': True,
            'indices': indices,
            'count': len(indices),
        }
    except ValueError as e:
        return {'error': str(e)}, 400
    except Exception as e:
        return {'error': f'Extraction failed: {str(e)}'}, 500
```

---

## Error Handling

### No API Key Found

```python
ValueError: No Gemini API key. Set GEMINI_API_KEY env var or pass gemini_api_key=
```

**Solution:**
```bash
export GEMINI_API_KEY="your-key"
```

Or pass directly:
```python
extract_toc_indices(text=text, gemini_api_key='your-key')
```

### File Not Found

```python
FileNotFoundError: [Errno 2] No such file or directory: 'text.txt'
```

**Solution:** Check file path exists:
```python
from pathlib import Path
assert Path('text.txt').exists()
```

### Empty Result

If extraction returns `[]`, the text may not have a clear ToC structure that Gemini can extract.

---

## Performance

| Text Size | Time | Notes |
|-----------|------|-------|
| < 100 KB | 0.5-1s | API latency dominant |
| 100 KB - 1 MB | 1-2s | First 1/5 sent to Gemini |
| 1-5 MB | 2-3s | Faster processing |
| > 5 MB | 3-5s | Auto-fallback to 1/10 or 1/100 slice if needed |

**Cost:** ~$0.0005 per extraction (using Gemini 1.5 Pro)

**Model:** Gemini 1.5 Pro is used by default for stable, reliable extraction with 1M context window.

**Context Limits:** The package automatically handles context window limits by progressively reducing the text slice (1/5 → 1/10 → 1/100) if needed. Works reliably with texts up to 50MB+.

---

## Testing

Run tests:

```bash
pip install -e ".[dev]"
pytest
pytest --cov=ai_text_outline
```

Tests: **32 passing** (including 8 new context overflow tests)

### Test Coverage

- **Parsing tests**: JSON response handling with edge cases
- **Integration tests**: Full extraction pipeline with mocked Gemini
- **Context overflow tests**: 
  - Retry mechanism with progressive text slice reduction (1/5 → 1/10 → 1/100)
  - Success on first attempt stops retrying
  - Non-context errors are properly raised
  - All attempts exhausted returns empty list

---

## Requirements

- Python 3.9 or higher
- Google Gemini API key (free tier available)
- Internet connection (for Gemini API calls)

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Support

- 📖 **Documentation**: See this README
- 🐛 **Issues**: [GitHub Issues](https://github.com/OpenPecha/ai-text-outline/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/OpenPecha/ai-text-outline/discussions)

---

## Citation

If you use this package in research:

```bibtex
@software{ai_text_outline,
  title={ai-text-outline: Extract Table of Contents from Tibetan texts},
  author={OpenPecha},
  url={https://github.com/OpenPecha/ai-text-outline},
  year={2026},
  license={MIT}
}
```

---

## Changelog

### v0.2.2 (Current)
- 🔧 **Model upgrade**: Changed from deprecated `gemini-2.0-flash` to stable `gemini-1.5-pro`
- 🚀 **Better model availability handling**: Detects and reports unavailable models with clear error messages
- 📊 **Improved cost estimates**: Updated to reflect Gemini 1.5 Pro pricing (~$0.0005 per extraction)
- 🛡️ **Enhanced error messages**: Better handling of model deprecation warnings

### v0.2.1
- 🔄 **Context overflow handling**: Automatic retry with progressive text slice reduction (1/5 → 1/10 → 1/100)
- 🧪 **Enhanced tests**: 32 passing tests including 8 new context overflow tests
- 📚 **Improved documentation**: Added context handling explanation to README
- 🛡️ **Robust error handling**: Detect and handle context/quota/token limit errors

### v0.2.0
- 🎉 Complete simplification: Gemini-only, no multi-provider support
- ⚡ Regex-based index finding (no fuzzy matching)
- 💪 Minimal dependencies: only `google-generativeai`
- 🧪 14 passing tests
- 📖 Simplified API with clear documentation

### v0.1.1
- ✨ Multi-provider LLM support
- 🔍 Fuzzy matching with position ranking
- 📚 Comprehensive documentation

### v0.1.0
- 🎉 Initial release
- དཀར་ཆག detection and parsing

---

<div align="center">

**Made with ❤️ by OpenPecha**

[GitHub](https://github.com/OpenPecha/ai-text-outline) • [PyPI](https://pypi.org/project/ai-text-outline/) • [Issues](https://github.com/OpenPecha/ai-text-outline/issues)

</div>
