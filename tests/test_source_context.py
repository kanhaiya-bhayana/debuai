"""
Tests for debugai/source_context.py — reading local source around a failure.
Uses tmp_path so no real project files are touched.
"""
from debugai.source_context import read_source_context

# 5-line sample file
SAMPLE = "def parse_input(raw):\n    return int(raw)\n\nx = 1\ny = 2\n"


def _write(tmp_path, name, text=SAMPLE):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


class TestReadSourceContext:

    def test_returns_numbered_snippet_with_marker(self, tmp_path):
        path = _write(tmp_path, "parser.py")
        out = read_source_context(path, 2, radius=1)
        assert "-> 2 |" in out                 # failing line marked
        assert "return int(raw)" in out
        assert "def parse_input" in out         # line 1 (radius)
        assert "y = 2" not in out               # line 5 outside radius

    def test_marks_only_the_failing_line(self, tmp_path):
        path = _write(tmp_path, "a.py")
        out = read_source_context(path, 1, radius=0)
        assert out.startswith("-> 1 |")
        assert out.count("->") == 1

    def test_accepts_string_line_number(self, tmp_path):
        # parsers return the line number as a string
        path = _write(tmp_path, "a.py")
        assert "-> 2 |" in read_source_context(path, "2", radius=0)

    def test_radius_clamps_to_file_bounds(self, tmp_path):
        path = _write(tmp_path, "a.py")
        out = read_source_context(path, 1, radius=10)
        assert "-> 1 |" in out
        assert len(out.splitlines()) == 5       # whole file, no negative lines

    def test_missing_file_returns_none(self, tmp_path):
        assert read_source_context(str(tmp_path / "nope.py"), 3) is None

    def test_none_file_returns_none(self):
        assert read_source_context(None, 3) is None

    def test_none_line_returns_none(self, tmp_path):
        assert read_source_context(_write(tmp_path, "a.py"), None) is None

    def test_non_integer_line_returns_none(self, tmp_path):
        assert read_source_context(_write(tmp_path, "a.py"), "not-a-number") is None

    def test_out_of_range_line_returns_none(self, tmp_path):
        path = _write(tmp_path, "a.py")
        assert read_source_context(path, 999) is None
        assert read_source_context(path, 0) is None
