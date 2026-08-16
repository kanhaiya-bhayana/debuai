import re
from .base import StackTraceParser


class JavaParser(StackTraceParser):

    LANGUAGE = "java"

    def match(self, log: str) -> bool:
        # Java frames always contain (ClassName.java:lineNumber)
        # This is the most reliable Java-specific signal
        return bool(re.search(r'\(.+\.java:\d+\)', log))

    def extract_frames(self, log: str):
        """
        Extract method names from Java stack frames.
        Java frame format:
            at com.example.package.ClassName.methodName(FileName.java:42)

        Returns innermost frame first (frames[0] = failure origin).
        """
        frames = re.findall(
            r'at\s+([\w$.]+)\s*\(\w+\.java:\d+\)',
            log
        )
        # Java traces list frames innermost-first already
        return frames

    def extract_exception_type(self, log: str) -> str:
        """
        Handles both short and fully-qualified Java exception names:
            NullPointerException
            java.lang.NullPointerException
        """
        # Fully qualified: java.lang.NullPointerException
        match = re.search(r'([\w$.]+(?:Exception|Error))', log)
        if match:
            # Return just the short name (last segment)
            return match.group(1).split(".")[-1]
        return "UnknownException"

    def extract_location(self, log: str):
        """Return (file, line, function) for the failure origin frame."""
        match = re.search(
            r'at\s+([\w$.]+)\s*\((\w+\.java):(\d+)\)',
            log
        )
        if match:
            return match.group(2), match.group(3), match.group(1)
        return None, None, None