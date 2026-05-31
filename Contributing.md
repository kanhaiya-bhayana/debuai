# Contributing to DebugAI

Thanks for your interest in contributing! DebugAI is open source and welcomes contributions of all kinds — bug fixes, new language parsers, AI provider support, documentation, and more.

---

## Getting Started

**1. Fork and clone the repo:**
```bash
git clone https://github.com/kanhaiya-bhayana/debuai.git
cd debuai
```

**2. Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

**3. Install dependencies:**
```bash
pip install -e ".[dev]"
```

**4. Set your API key:**
```bash
cp .env.example .env
# Add your key to .env
export OPENAI_API_KEY=your_key_here
```

**5. Run the test suite:**
```bash
python -m pytest tests/ -v
```

All 80+ tests should pass before you start making changes.

---

## Making Changes

**Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

**Branch naming convention:**
- `feature/` — new functionality
- `fix/` — bug fixes
- `parser/` — new language parser
- `docs/` — documentation only

---

## Adding a New Language Parser

This is one of the most valuable contributions. Here's the pattern:

**1. Create `debugai/parser/yourlanguage.py`:**
```python
import re
from .base import StackTraceParser

class YourLanguageParser(StackTraceParser):

    def match(self, log: str) -> bool:
        # Return True if this log looks like your language's trace
        return "your_unique_signal" in log

    def extract_frames(self, log: str):
        # Return list of function names, innermost first
        frames = re.findall(r'your_pattern', log)
        return frames

    def extract_exception_type(self, log: str) -> str:
        match = re.search(r'your_exception_pattern', log)
        return match.group(1) if match else "UnknownException"
```

**2. Register it in `debugai/parser/registry.py`:**
```python
from .yourlanguage import YourLanguageParser

PARSERS = [
    PythonParser(),
    JavaParser(),
    GoParser(),
    CSharpParser(),
    NodeParser(),
    YourLanguageParser(),   # add here, broadest matchers last
]
```

**3. Add tests in `tests/test_parsers.py`** — at minimum:
- `test_match_your_language` — confirms match() returns True
- `test_no_match_python` — confirms no false positives
- `test_extract_frames_not_empty` — confirms frames are extracted
- `test_extract_exception_type` — confirms exception is detected

---

## Adding a New AI Provider

**1. Create `debugai/providers/yourprovider.py`:**
```python
import os
from .base import AIProvider

class YourProvider(AIProvider):

    def name(self) -> str:
        return "YourProvider"

    def is_available(self) -> bool:
        return bool(os.getenv("YOURPROVIDER_API_KEY"))

    def analyze(self, prompt: str) -> str:
        # Call your provider's API and return raw text
        ...
```

**2. Register in `debugai/providers/__init__.py`:**
```python
from .yourprovider import YourProvider

PROVIDERS = [
    OpenAIProvider(),
    AnthropicProvider(),
    NvidiaProvider(),
    YourProvider(),
]
```

---

## Before Submitting a PR

```bash
# Run the full test suite
python -m pytest tests/ -v

# Make sure your feature has tests
# Make sure all existing tests still pass
```

**PR checklist:**
- [ ] Tests written and passing
- [ ] Existing tests unaffected
- [ ] README updated if adding a new feature/language/provider
- [ ] Branch is up to date with `main`

---

## Reporting Bugs

Open an issue with:
- Your OS and Python version
- The stack trace you were trying to analyse (redact sensitive info)
- The command you ran
- What you expected vs what happened

---

## Questions?

Open a GitHub Discussion or drop a comment on the relevant issue.