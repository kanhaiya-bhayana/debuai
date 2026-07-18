import json
import re
from abc import ABC, abstractmethod


class AIProvider(ABC):

    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name, e.g. 'OpenAI'."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the required env var / credentials are present."""
        raise NotImplementedError

    @abstractmethod
    def analyze(self, prompt: str) -> str:
        """Send prompt to the model and return raw text response."""
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    #  Prompt                                                             #
    # ------------------------------------------------------------------ #

    def build_prompt(self, log: str) -> str:
        return f"""You are a senior software engineer debugging a production issue.

Respond ONLY with a JSON object — no explanation, no markdown, no code fences.

The JSON must follow this exact schema:
{{
  "root_cause": "A concise explanation of why this error occurred.",
  "fix": "The specific code change or action needed to fix it.",
  "prevention": "How to prevent this class of error in future.",
  "confidence": "high | medium | low"
}}

Confidence guide:
- high   → the stack trace clearly identifies the cause
- medium → likely cause identified but some context is missing
- low    → not enough information to be certain

Stack trace:
{log}
"""

    # ------------------------------------------------------------------ #
    #  Response parsing                                                   #
    # ------------------------------------------------------------------ #

    def parse_response(self, text: str) -> dict:
        """
        Parse the model response into a structured dict.

        Priority:
          1. Strict JSON parse
          2. Extract the { } block (handles models that add commentary)
          3. Graceful fallback — return raw text as root_cause

        Always guarantees keys: root_cause, fix, prevention, confidence.
        """
        FALLBACK_CONFIDENCE = "low"

        def _fill_missing(d: dict) -> dict:
            d.setdefault("root_cause", "Could not parse AI response.")
            d.setdefault("fix", "")
            d.setdefault("prevention", "")
            d.setdefault("confidence", FALLBACK_CONFIDENCE)
            if d["confidence"] not in ("high", "medium", "low"):
                d["confidence"] = FALLBACK_CONFIDENCE
            return d

        # 1. Strict parse
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return _fill_missing(result)
        except (json.JSONDecodeError, ValueError):
            pass

        # 2. Extract the JSON block (first '{' to last '}', so nested
        #    objects wrapped in commentary survive rather than truncating
        #    at the first inner '}').
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, dict):
                    return _fill_missing(result)
            except (json.JSONDecodeError, ValueError):
                pass

        # 3. Fallback
        return {
            "root_cause": text.strip() or "No response from model.",
            "fix": "",
            "prevention": "",
            "confidence": FALLBACK_CONFIDENCE,
        }