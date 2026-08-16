import re
from .base import StackTraceParser


class CSharpParser(StackTraceParser):

    LANGUAGE = "csharp"

    def match(self, log: str) -> bool:
        # C# frames look like: at Namespace.Class.Method()
        # Key distinction from Java: no ".java:" file references
        has_at_frames = bool(re.search(r'at\s+[\w.]+\(', log))
        has_exception = bool(re.search(r'\w+Exception', log))
        is_not_java = ".java:" not in log
        return has_at_frames and has_exception and is_not_java

    def extract_frames(self, log: str):
        # Returns innermost frame first (matches convention of other parsers)
        frames = re.findall(r'at\s+([\w.<>[\]]+(?:\(.*?\))?)', log)
        return frames  # C# traces are already innermost-first

    def extract_exception_type(self, log: str) -> str:
        match = re.search(r'(\w+Exception)', log)
        if match:
            return match.group(1)
        return "UnknownException"

    def extract_location(self, log: str):
        """Return (file, line, function) for the failure origin frame."""
        # C# frames optionally include file info:
        # at Class.Method() in /path/to/File.cs:line 42
        match = re.search(
            r'at\s+([\w.<>]+\(.*?\))\s+in\s+(.+):line\s+(\d+)', log
        )
        if match:
            return match.group(2), match.group(3), match.group(1)
        # No file info — derive from class name
        frame_match = re.search(r'at\s+([\w.]+)\(', log)
        if frame_match:
            return None, None, frame_match.group(1)
        return None, None, None