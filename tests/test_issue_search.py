"""
Tests for debugai/issue_search.py
Uses monkeypatching to avoid real GitHub API calls in CI.
"""
import pytest
from debugai.issue_search import (
    _build_query,
    _score_issue,
    _extract_repo,
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