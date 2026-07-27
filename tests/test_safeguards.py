"""
Tests for edge cases and safeguards — empty input, encoding, oversized logs,
missing API key behaviour, and unrecognised formats.
"""
import os
import pytest
import tempfile
from debugai.analyzer import extract_all_stack_traces, extract_exception_type
from debugai.ai_analyzer import analyze_with_ai


# ── Input edge cases ──────────────────────────────────────────────────────────

class TestInputEdgeCases:

    def test_empty_string_no_traces(self):
        assert extract_all_stack_traces("") == []

    def test_whitespace_only_no_traces(self):
        assert extract_all_stack_traces("   \n\n\t  ") == []

    def test_single_line_no_traces(self):
        assert extract_all_stack_traces("Something went wrong") == []

    def test_log_noise_before_trace(self):
        """Trace buried inside log noise should still be extracted."""
        log = """\
INFO 2024-01-01 starting up
DEBUG connecting to db
INFO ready

Traceback (most recent call last):
  File "app.py", line 5, in run
    start()
RuntimeError: failed to start"""
        traces = extract_all_stack_traces(log)
        assert len(traces) == 1
        assert "RuntimeError" in traces[0]

    def test_trace_with_no_trailing_newline(self):
        """Traces that end at EOF (no blank line) must still be captured."""
        log = "Traceback (most recent call last):\n  File \"x.py\", line 1, in f\n    pass\nValueError: bad"
        traces = extract_all_stack_traces(log)
        assert len(traces) == 1

    def test_very_long_log_still_extracts(self):
        """A 1000-line log with a trace at the end should still find it."""
        noise = "\n".join([f"INFO log line {i}" for i in range(1000)])
        trace = "\nTraceback (most recent call last):\n  File \"x.py\", line 1, in go\n    fail()\nOSError: disk full"
        traces = extract_all_stack_traces(noise + trace)
        assert len(traces) == 1
        assert "OSError" in traces[0]


# ── Encoding edge cases ───────────────────────────────────────────────────────

class TestEncodingEdgeCases:

    def test_file_with_replacement_chars_does_not_crash(self, tmp_path):
        """
        Write a file with a non-UTF-8 byte, open it with errors='replace',
        and confirm analyze still works rather than crashing.
        """
        bad_file = tmp_path / "bad.log"
        # Write valid UTF-8 trace + one invalid byte sequence
        content = (
            b"Traceback (most recent call last):\n"
            b'  File "x.py", line 1, in go\n'
            b"    pass\n"
            b"ValueError: bad\xff\xfe value\n"
        )
        bad_file.write_bytes(content)

        with open(str(bad_file), encoding="utf-8", errors="replace") as f:
            log = f.read()

        # Should not raise, and the trace should still be found
        traces = extract_all_stack_traces(log)
        assert len(traces) == 1
        assert "ValueError" in traces[0]


# ── Missing API key safeguard ─────────────────────────────────────────────────

class TestMissingApiKey:

    def test_no_keys_returns_friendly_message(self, monkeypatch):
        """
        With all API keys unset, analyze_with_ai must return a dict
        with a human-readable root_cause — not raise an exception.
        """
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

        result = analyze_with_ai("Traceback...\nValueError: test")

        assert isinstance(result, dict)
        assert "root_cause" in result
        # Must be informative, not empty
        assert len(result["root_cause"]) > 10

    def test_unknown_provider_returns_friendly_message(self, monkeypatch):
        """A nonexistent provider must not crash, and must not be mislabelled
        as a runtime 'AI analysis failed' — it's a config error."""
        result = analyze_with_ai("some trace", provider_name="nonexistent_provider")
        assert isinstance(result, dict)
        assert "Unknown provider" in result["root_cause"]
        assert "nonexistent_provider" in result["root_cause"]
        assert result["root_cause"] != "AI analysis failed."
        assert result["confidence"] == "low"

    def test_wrong_provider_name_returns_friendly_message(self, monkeypatch):
        """Typo in --provider surfaces the available providers, not a stack error."""
        result = analyze_with_ai("some trace", provider_name="gpt5")
        assert "Unknown provider" in result["root_cause"]
        assert "gpt5" in result["root_cause"]
        # The actionable list of valid providers should be in the message.
        for name in ("openai", "anthropic", "nvidia"):
            assert name in result["root_cause"]

    def test_requested_provider_without_key_names_the_env_var(self, monkeypatch):
        """--provider openai with no key should tell the user which var to set."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = analyze_with_ai("some trace", provider_name="openai")
        assert "OPENAI_API_KEY" in result["root_cause"]
        assert result["confidence"] == "low"


# ── Unrecognised format ───────────────────────────────────────────────────────

class TestUnrecognisedFormat:

    def test_json_log_no_crash(self):
        """JSON-formatted logs with no trace should return empty list."""
        json_log = '{"level": "info", "msg": "started", "ts": 1234567890}'
        assert extract_all_stack_traces(json_log) == []

    def test_nginx_access_log_no_crash(self):
        nginx = '127.0.0.1 - - [01/Jan/2024:00:00:01 +0000] "GET / HTTP/1.1" 200 1234'
        assert extract_all_stack_traces(nginx) == []

    def test_exception_type_on_garbage_returns_unknown(self):
        assert extract_exception_type("connection refused after 3 retries") == "UnknownException"
