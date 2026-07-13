"""
Tests for --json output schema and confidence score handling.
"""
import json
import pytest
from debugai.providers.base import AIProvider


# ── Concrete stub for testing AIProvider.parse_response ──────────────────────

class StubProvider(AIProvider):
    def name(self): return "Stub"
    def is_available(self): return True
    def analyze(self, prompt): return ""


provider = StubProvider()


# ── parse_response — valid JSON ───────────────────────────────────────────────

class TestParseResponseValid:

    def test_parses_all_four_keys(self):
        raw = json.dumps({
            "root_cause": "Null object accessed",
            "fix": "Add null check",
            "prevention": "Use Optional",
            "confidence": "high"
        })
        result = provider.parse_response(raw)
        assert result["root_cause"] == "Null object accessed"
        assert result["fix"] == "Add null check"
        assert result["prevention"] == "Use Optional"
        assert result["confidence"] == "high"

    def test_confidence_high(self):
        raw = json.dumps({"root_cause": "x", "fix": "y", "prevention": "z", "confidence": "high"})
        assert provider.parse_response(raw)["confidence"] == "high"

    def test_confidence_medium(self):
        raw = json.dumps({"root_cause": "x", "fix": "y", "prevention": "z", "confidence": "medium"})
        assert provider.parse_response(raw)["confidence"] == "medium"

    def test_confidence_low(self):
        raw = json.dumps({"root_cause": "x", "fix": "y", "prevention": "z", "confidence": "low"})
        assert provider.parse_response(raw)["confidence"] == "low"


# ── parse_response — missing / invalid keys ───────────────────────────────────

class TestParseResponseDefaults:

    def test_missing_confidence_defaults_to_low(self):
        raw = json.dumps({"root_cause": "x", "fix": "y", "prevention": "z"})
        result = provider.parse_response(raw)
        assert result["confidence"] == "low"

    def test_invalid_confidence_defaults_to_low(self):
        raw = json.dumps({"root_cause": "x", "fix": "y", "prevention": "z", "confidence": "very_sure"})
        result = provider.parse_response(raw)
        assert result["confidence"] == "low"

    def test_missing_fix_defaults_to_empty(self):
        raw = json.dumps({"root_cause": "x", "prevention": "z", "confidence": "high"})
        result = provider.parse_response(raw)
        assert result["fix"] == ""

    def test_missing_prevention_defaults_to_empty(self):
        raw = json.dumps({"root_cause": "x", "fix": "y", "confidence": "high"})
        result = provider.parse_response(raw)
        assert result["prevention"] == ""

    def test_all_required_keys_always_present(self):
        result = provider.parse_response("{}")
        for key in ("root_cause", "fix", "prevention", "confidence"):
            assert key in result


# ── parse_response — malformed input ─────────────────────────────────────────

class TestParseResponseMalformed:

    def test_json_block_inside_prose(self):
        """Model wraps JSON in explanation text — should still extract it."""
        raw = 'Here is my analysis:\n{"root_cause": "NPE", "fix": "check null", "prevention": "use optional", "confidence": "high"}\nHope that helps!'
        result = provider.parse_response(raw)
        assert result["root_cause"] == "NPE"
        assert result["confidence"] == "high"

    def test_nested_json_block_inside_prose(self):
        """Nested JSON wrapped in prose — greedy extraction must capture the
        full object, not truncate at the first inner '}'."""
        raw = (
            'Sure, here is the analysis:\n'
            '{"root_cause": "NPE", "fix": "check null", "prevention": "use optional", '
            '"confidence": "high", "context": {"file": "a.py", "line": 42}}\n'
            'Let me know if you need more.'
        )
        result = provider.parse_response(raw)
        assert result["root_cause"] == "NPE"
        assert result["confidence"] == "high"

    def test_plain_text_fallback(self):
        """If no JSON at all, root_cause should contain the raw text."""
        raw = "The error is caused by a missing null check."
        result = provider.parse_response(raw)
        assert "null check" in result["root_cause"]
        assert result["confidence"] == "low"

    def test_empty_string_fallback(self):
        result = provider.parse_response("")
        assert result["root_cause"] == "No response from model."
        assert result["confidence"] == "low"

    def test_broken_json_fallback(self):
        result = provider.parse_response('{"root_cause": "missing closing brace"')
        assert "root_cause" in result
        assert result["confidence"] == "low"


# ── build_prompt — confidence instructions present ────────────────────────────

class TestBuildPrompt:

    def test_prompt_includes_confidence_field(self):
        prompt = provider.build_prompt("some trace")
        assert "confidence" in prompt

    def test_prompt_includes_confidence_levels(self):
        prompt = provider.build_prompt("some trace")
        assert "high" in prompt
        assert "medium" in prompt
        assert "low" in prompt

    def test_prompt_includes_trace(self):
        prompt = provider.build_prompt("ValueError: bad value")
        assert "ValueError: bad value" in prompt

    def test_prompt_requests_json_only(self):
        prompt = provider.build_prompt("some trace")
        # Must instruct model to return only JSON
        assert "ONLY" in prompt or "only" in prompt