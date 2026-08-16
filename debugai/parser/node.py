import re
from .base import StackTraceParser


class NodeParser(StackTraceParser):

    LANGUAGE = "node"

    def match(self, log: str) -> bool:
        return ".js:" in log

    def extract_frames(self, log: str):
        return re.findall(r'at\s+(?:Object\.)?([^\s]+)\s+\([^\)]+\)', log)

    def extract_location(self, log: str):
        """
        Return (file, line, function) for the innermost Node frame that points
        at a real .js source file, skipping core frames like
        `node:internal/...` that aren't on disk.
        """
        for raw in log.splitlines():
            line = raw.strip()
            if not line.startswith("at "):
                continue

            # Framed location: at <func> (<file>:<line>:<col>)
            m = re.search(r'\(([^()]+):(\d+):\d+\)', line)
            if m:
                file, lineno = m.group(1), m.group(2)
                func = line[3:line.rindex("(")].strip() or None
            else:
                # Anonymous frame: at <file>:<line>:<col>
                m = re.search(r'at\s+([^\s(]+):(\d+):\d+', line)
                if not m:
                    continue
                file, lineno, func = m.group(1), m.group(2), None

            if ".js" not in file:
                continue  # skip node:internal and other non-source frames
            return file, lineno, func

        return None, None, None