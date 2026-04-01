# Ready to Upload to PyPI

Your package has been built and verified successfully!

```
dist/ai_text_outline-0.1.0-py3-none-any.whl ✓
dist/ai_text_outline-0.1.0.tar.gz ✓
```

## Quick Upload Instructions

### 1. Create PyPI Account (if you don't have one)
- Go to: https://pypi.org/account/register/
- Create account
- Verify email
- Create API token in Account Settings → API tokens
- Copy token (starts with `pypi-`)

### 2. Configure Authentication

Create file: `~/.pypirc` (or `%APPDATA%\pip\.pypirc` on Windows)

```ini
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = YOUR_PYPI_TOKEN_HERE
```

Replace `YOUR_PYPI_TOKEN_HERE` with your actual token.

### 3. Upload to PyPI

From project directory:
```bash
twine upload dist/*
```

That's it! After successful upload:
- Package will be live on https://pypi.org/project/ai_text_outline/
- Anyone can install with: `pip install ai_text_outline`

## Verify Installation Works

After upload (wait 1-2 minutes):

```bash
pip install ai_text_outline

# Test it
python -c "from ai_text_outline import extract_toc_indices; print('Success!')"
```

## Optional: Test Upload First

Upload to test.pypi.org first (safe):

```bash
twine upload --repository testpypi dist/*
```

Then test install:
```bash
pip install --index-url https://test.pypi.org/simple/ ai_text_outline
```

---

## Package Info

**Name:** ai_text_outline  
**Version:** 0.1.0  
**Description:** Extract Table of Contents from Tibetan texts  
**Author:** OpenPecha  
**License:** MIT  

### Installation Options

```bash
# Basic (no LLM provider)
pip install ai_text_outline

# With Gemini support
pip install ai_text_outline[gemini]

# With OpenAI support
pip install ai_text_outline[openai]

# With Claude support  
pip install ai_text_outline[claude]

# With all providers
pip install ai_text_outline[all]

# With dev tools
pip install ai_text_outline[dev]
```

---

**Ready? Run:** `twine upload dist/*`
