from .python import PythonParser
from .java import JavaParser
from .go import GoParser
from .csharp import CSharpParser
from .node import NodeParser

# Order matters — most specific matchers first, broadest last.
#
# PythonParser  → anchors on "Traceback (most recent call last)"
# JavaParser    → anchors on ".java:\d+" in frames
# GoParser      → anchors on "goroutine \d+ [" or "panic:" + ".go:\d+"
# CSharpParser  → "at " + "Exception", no .java (broad — must come after Java)
# NodeParser    → anchors on ".js:" in frames
PARSERS = [
    PythonParser(),
    JavaParser(),
    GoParser(),
    CSharpParser(),
    NodeParser(),
]


def get_parser(log: str):
    for parser in PARSERS:
        if parser.match(log):
            return parser
    return None


def detect_language(log: str):
    """
    Return the language id ("python", "java", "go", "csharp", "node") of the
    parser that matches `log`, or None if nothing matches. Single source of
    truth for language detection, shared by the analyzer and the CLI.
    """
    parser = get_parser(log)
    return parser.LANGUAGE if parser else None