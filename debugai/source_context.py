"""
Read local source code around a failure line (for the --context flag).

Fail-soft by design: if the referenced file isn't on this machine (e.g. the
log came from somewhere else), every function returns None so callers can just
skip the source section.
"""
import os


def read_source_context(file_path: str, line, radius: int = 4):
    """
    Return a formatted snippet of `file_path` around `line`, or None.

    The snippet is line-numbered, with '->' marking the failing line:

        3 |     def parse_input(raw):
     -> 4 |         return int(raw)
        5 |
    """
    if not file_path or line is None:
        return None
    try:
        line = int(line)
    except (TypeError, ValueError):
        return None

    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None

    if not lines or line < 1 or line > len(lines):
        return None

    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    width = len(str(end))

    out = []
    for n in range(start, end + 1):
        marker = "->" if n == line else "  "
        out.append(f"{marker} {n:>{width}} | {lines[n - 1].rstrip()}")
    return "\n".join(out)
