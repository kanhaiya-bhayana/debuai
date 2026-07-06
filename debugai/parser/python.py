import re
from .base import StackTraceParser


class PythonParser(StackTraceParser):

    def match(self, log: str) -> bool:
        # Primary signal: standard Python traceback header
        if "Traceback (most recent call last)" in log:
            return True
        # Secondary: at least one File/line/in frame present (e.g. trimmed logs)
        if re.search(r'File ".+", line \d+, in \S+', log):
            return True
        return False

    def extract_frames(self, log: str):
        frames = re.findall(r'File ".+", line \d+, in ([^\n]+)', log)
        return list(reversed(frames))  # innermost first (failure origin at index 0)

    def extract_exception_type(self, log: str):
        # Match the final line: ExceptionType: message  OR  ExceptionType alone
        match = re.search(r'^(\w+(?:Error|Exception|Warning))\b', log, re.MULTILINE)
        if match:
            return match.group(1)
        # Fallback: last non-frame, non-Traceback line
        for line in reversed(log.splitlines()):
            line = line.strip()
            if line and not line.startswith(("File ", "Traceback", " ")):
                return line.split(":")[0]
        return "UnknownException"

    def extract_location(self, log: str):
        """Return (file, line_number, function) for the failure origin frame."""
        frames = re.findall(
            r'File "(.+)", line (\d+), in ([^\n]+)', log
        )
        if frames:
            # Last frame = innermost = failure origin
            file, line, func = frames[-1]
            return file, line, func.strip()
        return None, None, None
