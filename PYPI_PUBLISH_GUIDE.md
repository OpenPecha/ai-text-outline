# Publishing ai_text_outline to PyPI

## Step 1: Create a PyPI Account

1. Go to https://pypi.org/account/register/
2. Create an account with username and password
3. Verify your email address
4. Enable 2FA (recommended for security)

## Step 2: Create an API Token

1. Log into https://pypi.org/
2. Go to **Account Settings** → **API tokens**
3. Click **Add API token**
4. Name it: `ai_text_outline`
5. Scope: `Entire account` (or specific project once it exists)
6. Copy the token (you'll only see it once!)

**Token format:** `pypi-AgEIcHlwaS5vcmc...` (starts with `pypi-`)

## Step 3: Configure Credentials

### Option A: Use .pypirc (Recommended)

Create `~/.pypirc` file (Windows: `%APPDATA%\pip\.pypirc`):

```ini
[distutils]
index-servers =
    pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmc...
```

Replace the password with your actual token from Step 2.

### Option B: Use Environment Variable

```bash
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmc...
```

Then upload with:
```bash
twine upload dist/* -u __token__
```

## Step 4: Publish to PyPI

From the project directory:

```bash
# Build (if not already done)
python -m build

# Check for issues
twine check dist/*

# Upload to PyPI
twine upload dist/*

# You'll be prompted for username (__token__) and password (your token)
```

## Step 5: Verify

```bash
# Wait 1-2 minutes for PyPI to process

# Check it's live:
pip search ai_text_outline

# Or visit:
# https://pypi.org/project/ai_text_outline/

# Install it:
pip install ai_text_outline

# Test it works:
python -c "from ai_text_outline import extract_toc_indices; print('Success!')"
```

## Step 6: Update Version for Future Releases

Edit `pyproject.toml`:
```toml
version = "0.2.0"  # Increment version
```

Then rebuild and upload again.

## Troubleshooting

### "Invalid distribution" or "File already exists"
- Check `twine check dist/*` for errors
- Make sure version number is incremented for new uploads

### "HTTPError 403 Forbidden"
- Verify your token is correct
- Check username is `__token__` (not your PyPI username)
- Token may have expired or wrong scope

### "HTTPError 404 Not Found"
- Project doesn't exist yet (first upload) - this is normal
- PyPI will create it on first successful upload

## After Publishing

**Update README.md:**
```markdown
pip install ai_text_outline

# With specific LLM provider:
pip install ai_text_outline[gemini]
pip install ai_text_outline[openai]
pip install ai_text_outline[claude]

# With all providers:
pip install ai_text_outline[all]
```

**GitHub Release:**
```bash
git tag v0.1.0
git push origin v0.1.0
# Then create release on GitHub with release notes
```

## Commands Reference

```bash
# Build
python -m build

# Check
twine check dist/*

# Upload to PyPI
twine upload dist/*

# Upload to TestPyPI (for testing first)
twine upload --repository testpypi dist/*
# Install from TestPyPI:
# pip install --index-url https://test.pypi.org/simple/ ai_text_outline
```

---

**Package Details:**
- Name: `ai_text_outline`
- Current Version: `0.1.0`
- PyPI: https://pypi.org/project/ai_text_outline/
- Repository: https://github.com/OpenPecha/ai-text-outline
