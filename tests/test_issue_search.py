"""
Tests for debugai/issue_search.py
Uses monkeypatching to avoid real GitHub API calls in CI.
"""
import json
import urllib.error

import pytest

import debugai.issue_search as issue_search
from debugai.issue_search import (
    _build_query,
    _score_issue,
    _extract_repo,
    _fetch_issues,
    search_github_issues,
)

# ── _build_query ──────────────────────────────────────────────────────────────

class TestBuildQuery:

    def test_includes_exception_type(self):
        q = _build_query("ValueError", "parse_input")
        assert "ValueError" in q

    def test_includes_specific_frame(self):
        q = _build_query("NullPointerException", "calculateTotal")
        assert "calculateTotal" in q

    def test_excludes_generic_frame_main(self):
        q = _build_query("ValueError", "main")
        assert "main" not in q

    def test_excludes_generic_frame_run(self):
        q = _build_query("RuntimeError", "run")
        assert "run" not in q

    def test_handles_dotted_frame(self):
        """Dotted frame like OrderService.calculateTotal → uses calculateTotal"""
        q = _build_query("NullPointerException", "OrderService.calculateTotal")
        assert "calculateTotal" in q

    def test_handles_empty_frame(self):
        q = _build_query("ValueError", "")
        assert "ValueError" in q

    def test_unknown_exception_still_builds(self):
        q = _build_query("UnknownException", "some_func")
        assert q is not None


# ── _score_issue ──────────────────────────────────────────────────────────────

class TestScoreIssue:

    def _make_issue(self, title="", body="", state="open", comments=5):
        return {"title": title, "body": body, "state": state, "comments": comments}

    def test_exception_in_title_scores_high(self):
        issue = self._make_issue(title="ValueError when parsing input", comments=5)
        score = _score_issue(issue, "ValueError")
        assert score >= 10

    def test_closed_issue_scores_higher(self):
        open_issue   = self._make_issue(state="open",   comments=5)
        closed_issue = self._make_issue(state="closed", comments=5)
        assert _score_issue(closed_issue, "Error") > _score_issue(open_issue, "Error")

    def test_high_comment_count_scores_higher(self):
        few    = self._make_issue(comments=1)
        many   = self._make_issue(comments=15)
        assert _score_issue(many, "Error") > _score_issue(few, "Error")

    def test_low_comments_penalised(self):
        score = _score_issue(self._make_issue(comments=1), "Error")
        assert score < 0

    def test_exception_in_body_adds_score(self):
        no_body   = self._make_issue(body="")
        with_body = self._make_issue(body="We hit a ValueError here")
        assert _score_issue(with_body, "ValueError") > _score_issue(no_body, "ValueError")


# ── _extract_repo ─────────────────────────────────────────────────────────────

class TestExtractRepo:

    def test_extracts_owner_and_repo(self):
        url = "https://github.com/spring-projects/spring-framework/issues/123"
        assert _extract_repo(url) == "spring-projects/spring-framework"

    def test_handles_invalid_url(self):
        assert _extract_repo("not-a-url") == "unknown/repo"

    def test_handles_empty_string(self):
        assert _extract_repo("") == "unknown/repo"


# ── search_github_issues (mocked) ─────────────────────────────────────────────

class TestSearchGithubIssues:

    MOCK_ISSUES = [
        {
            "title": "ValueError: invalid literal for int() with base 10",
            "html_url": "https://github.com/python/cpython/issues/1",
            "state": "closed",
            "comments": 12,
            "body": "We hit a ValueError when parsing user input"
        },
        {
            "title": "ValueError in parse_input with non-numeric strings",
            "html_url": "https://github.com/example/app/issues/42",
            "state": "open",
            "comments": 4,
            "body": "Same ValueError issue"
        },
        {
            "title": "Unrelated issue about something else entirely",
            "html_url": "https://github.com/other/repo/issues/99",
            "state": "open",
            "comments": 1,
            "body": "Nothing relevant"
        },
    ]

    def test_returns_list(self, monkeypatch):
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: self.MOCK_ISSUES)
        results = search_github_issues("ValueError", "parse_input")
        assert isinstance(results, list)

    def test_returns_max_three(self, monkeypatch):
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: self.MOCK_ISSUES * 5)
        results = search_github_issues("ValueError", "parse_input")
        assert len(results) <= 3

    def test_result_has_required_keys(self, monkeypatch):
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: self.MOCK_ISSUES)
        results = search_github_issues("ValueError", "parse_input")
        if results:
            for key in ("title", "url", "state", "comments", "repo"):
                assert key in results[0]

    def test_empty_on_api_failure(self, monkeypatch):
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: [])
        results = search_github_issues("ValueError", "parse_input")
        assert results == []

    def test_empty_for_unknown_exception(self, monkeypatch):
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: self.MOCK_ISSUES)
        results = search_github_issues("UnknownException", "some_frame")
        assert results == []

    def test_filters_low_quality_issues(self, monkeypatch):
        """Issues with <2 comments and no exception match should be filtered out."""
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: [self.MOCK_ISSUES[2]])
        results = search_github_issues("ValueError", "parse_input")
        assert results == []

    def test_closed_issues_ranked_first(self, monkeypatch):
        monkeypatch.setattr("debugai.issue_search._fetch_issues", lambda q: self.MOCK_ISSUES)
        results = search_github_issues("ValueError", "parse_input")
        if len(results) >= 2:
            closed = [r for r in results if r["state"] == "closed"]
            assert len(closed) > 0


# ── _fetch_issues (urllib mocked) ─────────────────────────────────────────────

class _FakeResponse:
    """Minimal stand-in for the object urlopen returns (a context manager)."""

    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestFetchIssues:

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        # _fetch_issues memoises into a module-level dict — reset around each test.
        issue_search._cache.clear()
        yield
        issue_search._cache.clear()

    def _patch(self, monkeypatch, opener):
        # Never actually sleep for the rate-limit delay during tests.
        monkeypatch.setattr(issue_search.time, "sleep", lambda *a, **k: None)
        monkeypatch.setattr(issue_search.urllib.request, "urlopen", opener)

    def test_returns_items_on_success(self, monkeypatch):
        payload = json.dumps({"items": [{"title": "A"}, {"title": "B"}]}).encode()
        self._patch(monkeypatch, lambda req, timeout=None: _FakeResponse(payload))
        assert _fetch_issues("ValueError") == [{"title": "A"}, {"title": "B"}]

    def test_builds_expected_url_and_headers(self, monkeypatch):
        captured = {}

        def opener(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = req.headers
            captured["timeout"] = timeout
            return _FakeResponse(json.dumps({"items": []}).encode())

        self._patch(monkeypatch, opener)
        _fetch_issues("Null Pointer")

        assert captured["url"].startswith("https://api.github.com/search/issues?")
        assert "q=Null+Pointer" in captured["url"]
        assert "sort=reactions" in captured["url"]
        assert "order=desc" in captured["url"]
        assert "per_page=10" in captured["url"]
        # urllib capitalises header keys, so match on values instead.
        assert any("debuai-cli" in str(v) for v in captured["headers"].values())
        assert any("github" in str(v) for v in captured["headers"].values())
        assert captured["timeout"] == 8

    def test_missing_items_key_returns_empty(self, monkeypatch):
        self._patch(monkeypatch, lambda req, timeout=None: _FakeResponse(b"{}"))
        assert _fetch_issues("ValueError") == []

    def test_malformed_json_returns_empty(self, monkeypatch):
        self._patch(monkeypatch, lambda req, timeout=None: _FakeResponse(b"<html>nope</html>"))
        assert _fetch_issues("ValueError") == []

    def test_http_403_returns_empty(self, monkeypatch):
        def opener(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 403, "rate limited", {}, None)

        self._patch(monkeypatch, opener)
        assert _fetch_issues("ValueError") == []

    def test_http_500_returns_empty(self, monkeypatch):
        def opener(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 500, "server error", {}, None)

        self._patch(monkeypatch, opener)
        assert _fetch_issues("ValueError") == []

    def test_network_error_returns_empty(self, monkeypatch):
        def opener(req, timeout=None):
            raise urllib.error.URLError("no network")

        self._patch(monkeypatch, opener)
        assert _fetch_issues("ValueError") == []

    def test_result_is_cached(self, monkeypatch):
        calls = {"n": 0}
        payload = json.dumps({"items": [{"title": "cached"}]}).encode()

        def opener(req, timeout=None):
            calls["n"] += 1
            return _FakeResponse(payload)

        self._patch(monkeypatch, opener)
        first = _fetch_issues("ValueError")
        second = _fetch_issues("ValueError")
        assert first == second == [{"title": "cached"}]
        assert calls["n"] == 1  # second call served from cache, no second request

    def test_cache_key_is_normalised(self, monkeypatch):
        calls = {"n": 0}
        payload = json.dumps({"items": [{"title": "x"}]}).encode()

        def opener(req, timeout=None):
            calls["n"] += 1
            return _FakeResponse(payload)

        self._patch(monkeypatch, opener)
        _fetch_issues("ValueError")
        _fetch_issues("  valueerror ")  # same key after lower().strip()
        assert calls["n"] == 1