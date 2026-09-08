"""
End-to-end tests for the Typer CLI (debugai/cli.py) via CliRunner.

Covers the command wiring itself — flag handling, the stdin input path,
JSON vs Rich rendering, and the --ai/--issues/--context/--top branches —
which the unit tests for the underlying functions don't exercise.

Note: input is fed via stdin (the primary `cat log | debuai` path). The
file-path / literal-arg / clipboard branches depend on stdin being a TTY,
which CliRunner can't emulate, so they're covered by manual smoke tests.
"""
import json

from typer.testing import CliRunner

import debugai.cli as cli
from debugai.cli import app

runner = CliRunner()

PY_TRACE = (
    "Traceback (most recent call last):\n"
    '  File "app.py", line 3, in main\n'
    "    x = int(raw)\n"
    "ValueError: bad int\n"
)

MULTI_TRACE = PY_TRACE + (
    "\nTraceback (most recent call last):\n"
    '  File "b.py", line 1, in lookup\n'
    "    d['k']\n"
    "KeyError: 'k'\n"
)


class TestRichMode:

    def test_shows_exception_and_origin(self):
        r = runner.invoke(app, [], input=PY_TRACE)
        assert r.exit_code == 0
        assert "ValueError" in r.stdout
        assert "main" in r.stdout

    def test_no_stack_trace_message(self):
        r = runner.invoke(app, [], input="just some ordinary log noise\n")
        assert r.exit_code == 0
        assert "No stack trace detected" in r.stdout

    def test_ai_panels_rendered(self, monkeypatch):
        monkeypatch.setattr(
            cli, "analyze_with_ai",
            lambda *a, **k: {
                "root_cause": "NULLDEREF", "fix": "addcheck",
                "prevention": "validate", "confidence": "high",
            },
        )
        r = runner.invoke(app, ["--ai"], input=PY_TRACE)
        assert r.exit_code == 0
        assert "NULLDEREF" in r.stdout
        assert "addcheck" in r.stdout
        assert "HIGH" in r.stdout  # confidence rendered uppercase

    def test_issues_table_rendered(self, monkeypatch):
        monkeypatch.setattr(
            cli, "search_github_issues",
            lambda *a, **k: [
                {"title": "Fix the ValueError", "url": "https://github.com/o/r/issues/1",
                 "state": "closed", "comments": 12, "repo": "o/r"}
            ],
        )
        r = runner.invoke(app, ["--issues"], input=PY_TRACE)
        assert r.exit_code == 0
        assert "Related GitHub Issues" in r.stdout
        assert "o/r" in r.stdout

    def test_issues_none_found_message(self, monkeypatch):
        monkeypatch.setattr(cli, "search_github_issues", lambda *a, **k: [])
        r = runner.invoke(app, ["--issues"], input=PY_TRACE)
        assert r.exit_code == 0
        assert "No related GitHub issues found" in r.stdout

    def test_context_panel_rendered(self, tmp_path):
        src = tmp_path / "app.py"
        src.write_text("def main():\n    x = int('a')\n    return x\n")
        trace = (
            "Traceback (most recent call last):\n"
            f'  File "{src}", line 2, in main\n'
            "    x = int('a')\n"
            "ValueError: bad int\n"
        )
        r = runner.invoke(app, ["--context"], input=trace)
        assert r.exit_code == 0
        assert "Source Context" in r.stdout
        assert "int(" in r.stdout


class TestInputResolution:

    def test_paste_reads_clipboard(self, monkeypatch):
        monkeypatch.setattr(cli, "read_clipboard", lambda: PY_TRACE)
        r = runner.invoke(app, ["--paste", "--json"])
        assert r.exit_code == 0
        assert json.loads(r.stdout)["exception"] == "ValueError"

    def test_paste_clipboard_error_is_friendly(self, monkeypatch):
        def boom():
            raise cli.ClipboardError("no clipboard tool available")
        monkeypatch.setattr(cli, "read_clipboard", boom)
        r = runner.invoke(app, ["--paste"], input="")
        assert "no clipboard tool available" in r.stdout


class TestJsonMode:

    def test_json_keys(self):
        r = runner.invoke(app, ["--json"], input=PY_TRACE)
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["exception"] == "ValueError"
        assert data["failure_origin"] == "main"
        assert data["language"] == "python"
        assert isinstance(data["execution_chain"], list) and data["execution_chain"]

    def test_json_no_trace_error(self):
        r = runner.invoke(app, ["--json"], input="nothing to see here\n")
        assert r.exit_code == 0
        assert "error" in json.loads(r.stdout)

    def test_json_ai_block(self, monkeypatch):
        monkeypatch.setattr(
            cli, "analyze_with_ai",
            lambda *a, **k: {
                "root_cause": "rc", "fix": "fx",
                "prevention": "pv", "confidence": "high",
            },
        )
        r = runner.invoke(app, ["--json", "--ai"], input=PY_TRACE)
        data = json.loads(r.stdout)
        assert data["ai"] == {
            "root_cause": "rc", "fix": "fx", "prevention": "pv", "confidence": "high",
        }

    def test_json_issues_block(self, monkeypatch):
        monkeypatch.setattr(
            cli, "search_github_issues",
            lambda *a, **k: [
                {"title": "T", "url": "u", "state": "closed", "comments": 5, "repo": "o/r"}
            ],
        )
        r = runner.invoke(app, ["--json", "--issues"], input=PY_TRACE)
        data = json.loads(r.stdout)
        assert data["github_issues"][0]["repo"] == "o/r"

    def test_json_top_two_returns_list(self):
        r = runner.invoke(app, ["--json", "--top", "2"], input=MULTI_TRACE)
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["exception"] == "ValueError"
        assert data[1]["exception"] == "KeyError"

    def test_json_context_field(self, tmp_path):
        src = tmp_path / "app.py"
        src.write_text("def main():\n    x = int('a')\n    return x\n")
        trace = (
            "Traceback (most recent call last):\n"
            f'  File "{src}", line 2, in main\n'
            "    x = int('a')\n"
            "ValueError: bad int\n"
        )
        r = runner.invoke(app, ["--json", "--context"], input=trace)
        data = json.loads(r.stdout)
        assert data["source_context"] is not None
        assert "int(" in data["source_context"]
