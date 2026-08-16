import re
from .base import StackTraceParser


class GoParser(StackTraceParser):

    LANGUAGE = "go"

    def match(self, log: str) -> bool:
        # Go panics always start with "goroutine N [status]:"
        # or "panic:" — either is a strong signal
        has_goroutine = bool(re.search(r'goroutine\s+\d+\s+\[', log))
        has_panic = "panic:" in log
        has_go_files = bool(re.search(r'\.go:\d+', log))
        return (has_goroutine or has_panic) and has_go_files

    def extract_frames(self, log: str):
        """
        Extract function names from Go stack frames.

        Go stack frame format (two lines per frame):
            main.functionName(args)
            /path/to/file.go:42 +0x1a3

        Returns innermost frame first (frames[0] = failure origin).
        """
        # Match the function name line (package.FuncName or package.(*Type).Method)
        frames = re.findall(
            r'^([\w/$.]+\.(?:\(\*?[\w.]+\)\.)?[\w]+)\(',
            log,
            re.MULTILINE
        )

        # Filter out runtime internals unless they're the only frames
        user_frames = [f for f in frames if not f.startswith("runtime.")]
        return user_frames if user_frames else frames

    def extract_exception_type(self, log: str) -> str:
        """
        Go doesn't have exception types — it has panic values.
        Extract the panic message type or signal name.
        Examples:
            panic: runtime error: index out of range [3] with length 3
            panic: interface conversion: interface {} is nil, not string
            signal SIGSEGV: segmentation violation
        """
        # signal panic
        sig_match = re.search(r'signal\s+(SIG\w+)', log)
        if sig_match:
            return sig_match.group(1)

        # runtime panic type
        runtime_match = re.search(r'panic:\s+runtime error:\s+(.+?)(?:\n|$)', log)
        if runtime_match:
            # Shorten to the error class
            msg = runtime_match.group(1).strip()
            if "index out of range" in msg:
                return "IndexOutOfRangeError"
            if "nil pointer" in msg:
                return "NilPointerError"
            if "slice bounds" in msg:
                return "SliceBoundsError"
            return "RuntimePanic"

        # general panic
        panic_match = re.search(r'panic:\s+(.+?)(?:\n|$)', log)
        if panic_match:
            return "Panic"

        return "GoPanic"

    def extract_location(self, log: str):
        """Return (file, line, function) for the failure origin frame."""
        # Go frames: function line followed by file:line
        func_match = re.search(
            r'^([\w/$.]+\.[\w]+)\(.*?\)\n\s+(.+\.go):(\d+)',
            log,
            re.MULTILINE
        )
        if func_match:
            return func_match.group(2), func_match.group(3), func_match.group(1)
        return None, None, None