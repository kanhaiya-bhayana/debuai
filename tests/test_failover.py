"""
Tests for provider runtime failover in debugai/ai_analyzer.py.

Uses fake providers swapped into ai_analyzer.PROVIDERS so no real SDK/network
is touched. Failover only applies to auto-detect mode; an explicit provider is
honoured with no failover.
"""
import debugai.ai_analyzer as ai_analyzer
from debugai.ai_analyzer import analyze_with_ai


class FakeProvider:
    def __init__(self, name, available=True, result=None, error=None):
        self._name = name
        self._available = available
        self._result = result
        self._error = error
        self.calls = 0

    def name(self):
        return self._name

    def is_available(self):
        return self._available

    def build_prompt(self, log, source_context=None):
        return log

    def analyze(self, prompt):
        self.calls += 1
        if self._error:
            raise self._error
        return self._result

    def parse_response(self, text):
        return {"root_cause": text, "fix": "", "prevention": "", "confidence": "high"}


class TestFailover:

    def test_fails_over_to_next_available_provider(self, monkeypatch):
        p1 = FakeProvider("A", error=RuntimeError("boom-A"))
        p2 = FakeProvider("B", result="B-analysis")
        monkeypatch.setattr(ai_analyzer, "PROVIDERS", [p1, p2])

        result = analyze_with_ai("trace")
        assert result["root_cause"] == "B-analysis"
        assert p1.calls == 1 and p2.calls == 1  # first tried, then failed over

    def test_first_success_short_circuits(self, monkeypatch):
        p1 = FakeProvider("A", result="A-analysis")
        p2 = FakeProvider("B", result="B-analysis")
        monkeypatch.setattr(ai_analyzer, "PROVIDERS", [p1, p2])

        result = analyze_with_ai("trace")
        assert result["root_cause"] == "A-analysis"
        assert p2.calls == 0  # never reached — no needless second call

    def test_skips_unavailable_providers(self, monkeypatch):
        p1 = FakeProvider("A", available=False, result="A-analysis")
        p2 = FakeProvider("B", available=True, result="B-analysis")
        monkeypatch.setattr(ai_analyzer, "PROVIDERS", [p1, p2])

        result = analyze_with_ai("trace")
        assert result["root_cause"] == "B-analysis"
        assert p1.calls == 0  # not available, never attempted

    def test_all_available_fail_returns_last_error(self, monkeypatch):
        p1 = FakeProvider("A", error=RuntimeError("boom-A"))
        p2 = FakeProvider("B", error=RuntimeError("boom-B"))
        monkeypatch.setattr(ai_analyzer, "PROVIDERS", [p1, p2])

        result = analyze_with_ai("trace")
        assert result["root_cause"] == "AI analysis failed."
        assert "boom-B" in result["fix"]  # last error surfaced
        assert result["confidence"] == "low"

    def test_explicit_provider_does_not_fail_over(self, monkeypatch):
        p1 = FakeProvider("openai", error=RuntimeError("boom-openai"))
        p2 = FakeProvider("anthropic", result="should-not-be-used")
        monkeypatch.setattr(ai_analyzer, "PROVIDERS", [p1, p2])

        result = analyze_with_ai("trace", provider_name="openai")
        assert result["root_cause"] == "AI analysis failed."
        assert "boom-openai" in result["fix"]
        assert p2.calls == 0  # explicit choice honoured — no failover

    def test_no_available_providers_returns_config_message(self, monkeypatch):
        p1 = FakeProvider("A", available=False)
        p2 = FakeProvider("B", available=False)
        monkeypatch.setattr(ai_analyzer, "PROVIDERS", [p1, p2])

        result = analyze_with_ai("trace")
        assert "No AI provider configured" in result["root_cause"]
        assert p1.calls == 0 and p2.calls == 0
