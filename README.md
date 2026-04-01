# ai_text_outline

Extract Table of Contents from Tibetan texts and return character indices of where each section begins.

## Features

- **Automatic ToC detection** using དཀར་ཆག (dkar chag) markers
- **Regex-based extraction** for structured ToC sections
- **LLM-powered fallback** using Google Gemini, OpenAI, or Anthropic Claude
- **Multi-provider support** — choose your preferred LLM
- **Fuzzy matching** to locate sections even with text variations
- **Efficient API usage** — only sends relevant ToC sections to the LLM, not the entire text

## Installation

### Basic Installation

```bash
pip install ai_text_outline
```

### With Specific LLM Provider

Install with support for a specific LLM provider:

```bash
# For Google Gemini (recommended)
pip install ai_text_outline[gemini]

# For OpenAI
pip install ai_text_outline[openai]

# For Anthropic Claude
pip install ai_text_outline[claude]

# For all providers
pip install ai_text_outline[all]
```

### For Development

```bash
pip install -e ".[dev,all]"
```

## Configuration

### Environment Variables

The package requires an API key for at least one LLM provider. Set one of the following environment variables:

#### Google Gemini (Recommended)
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

Get your API key at: https://ai.google.dev/

#### OpenAI
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

#### Anthropic Claude
```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

#### Multiple Providers

If you set multiple API keys, the package uses this priority order:
1. **Gemini** (if `GEMINI_API_KEY` is set)
2. **OpenAI** (if `OPENAI_API_KEY` is set)
3. **Claude** (if `ANTHROPIC_API_KEY` is set)

You can override the default provider by passing `provider` parameter to the function.

## Usage

### Basic Usage

Extract ToC from a file:

```python
from ai_text_outline import extract_toc_indices

# Extract from file
indices = extract_toc_indices(file_path="path/to/tibetan_text.txt")
print(indices)  # [150, 2450, 5200, ...]
```

Extract from text string:

```python
# Extract from text string
text = "..."  # Your Tibetan text
indices = extract_toc_indices(text=text)
```

### Advanced Configuration

```python
indices = extract_toc_indices(
    text=text,
    provider="gemini",              # Explicitly choose provider
    model="gemini-1.5-pro",         # Use specific model
    chars_per_page=2000,            # Chars per page (for estimation)
    fuzzy_threshold=0.9,            # Fuzzy match threshold (0.0-1.0)
)
```

### For Backend Integration

Your backend should:

1. **Install the package**:
   ```bash
   pip install ai_text_outline[gemini]
   ```

2. **Set the API key** in your environment:
   ```bash
   export GEMINI_API_KEY="your-key"
   ```

3. **Call the function** when a user clicks the ToC extraction button:
   ```python
   from ai_text_outline import extract_toc_indices

   @app.post("/extract-toc")
   def extract_toc(request):
       # Option 1: From file path
       file_path = request.json.get("file_path")
       
       # Option 2: From text content
       text = request.json.get("text")
       
       try:
           indices = extract_toc_indices(file_path=file_path, text=text)
           return {"success": True, "indices": indices}
       except ValueError as e:
           return {"success": False, "error": str(e)}, 400
   ```

## Return Value

Returns a **sorted list of integers** representing character indices where each ToC section begins:

```python
[150, 2450, 5200]  # Character positions in the text
```

If no ToC is found, returns an empty list: `[]`

## How It Works

### Pipeline Overview

1. **Load text** from file or string
2. **Find ToC section** using དཀར་ཆག markers (or use first quarter/100 pages as fallback)
3. **Extract ToC entries** using regex patterns
4. **Fallback to LLM** if regex fails (sends only ToC section, not whole text)
5. **Locate section starts** by page markers (if present) or fuzzy title matching
6. **Return sorted indices**

### ToC Section Detection

The package looks for དཀར་ཆག (Table of Contents marker) in the text:
- Takes the **first occurrence** as ToC start
- Takes the **last occurrence** as ToC body end anchor
- Extends until a **double newline** or **4 more pages**, whichever comes first

### Entry Extraction

Attempts regex patterns first:
- Tibetan text + delimiter (༎ ། . …) + page number
- Supports both Arabic (0-9) and Tibetan numerals (༠-༩)

If regex fails, sends the extracted ToC section to LLM for structured extraction (JSON format).

### Section Location

For each ToC entry:
1. If page numbers exist in text: finds page marker, returns position after it
2. If no page markers: fuzzy matches the title using `rapidfuzz`
   - Searches within ±50% of expected page offset
   - Picks best match with similarity ≥ 90%
   - If no match found: skips silently (not included in output)

## Error Handling

- **ValueError**: Raised if neither or both of `file_path`/`text` provided
- **FileNotFoundError**: Raised if file doesn't exist
- **UnicodeDecodeError**: Raised if file is not UTF-8 encoded
- **ValueError**: Raised if no API key is configured

For LLM errors (rate limits, auth failures), the package logs a warning and returns an empty list `[]`.

## Logging

Enable debug logging to see detailed extraction steps:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
indices = extract_toc_indices(text=text)
```

Debug output shows:
- Text length loaded
- Provider and model used
- Whether དཀར་ཆག section was found
- Number of ToC entries extracted
- Which entries couldn't be located

## Requirements

- Python 3.9+
- At least one LLM API key (Gemini, OpenAI, or Claude)

## Performance Notes

- Typical Tibetan texts (< 1000 pages): ~1-2 seconds
- Large texts (> 1000 pages): ~2-5 seconds depending on ToC complexity
- Only sends ToC section to LLM (not full text) → much cheaper API calls

## Troubleshooting

### "No API key found" Error

Make sure you've set one of these environment variables:
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Check with:
```bash
echo $GEMINI_API_KEY
```

### LLM Returns Empty Response

This typically means:
1. The ToC format is unusual (try looking at the text manually)
2. The LLM couldn't identify the structure (try a different model or provider)
3. API rate limit reached (wait and retry)

Enable debug logging to see what text was sent to the LLM:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Regex Extraction Works But Indices Are Wrong

The fuzzy matching threshold (default 0.9) may be too strict. Try:
```python
indices = extract_toc_indices(text=text, fuzzy_threshold=0.85)
```

## License

MIT License — See LICENSE file for details
