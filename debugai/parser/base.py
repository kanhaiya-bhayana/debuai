class StackTraceParser:

    LANGUAGE = None  # subclasses set their language id, e.g. "python"

    def match(self, log: str) -> bool:
        """
        Determine if this parser can handle the log.
        """
        raise NotImplementedError

    def extract_frames(self, log: str):
        """
        Extract stack frames.
        """
        raise NotImplementedError