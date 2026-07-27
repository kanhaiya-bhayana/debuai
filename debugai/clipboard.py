"""
Cross-platform clipboard reading for the --paste flag.

Uses the platform's native clipboard tool via subprocess (no third-party
dependency), mirroring the stdlib-only approach used elsewhere in the project:

    macOS    -> pbpaste
    Windows  -> powershell Get-Clipboard
    Linux    -> wl-paste (Wayland), else xclip, else xsel
"""
import shutil
import subprocess
import sys


class ClipboardError(Exception):
    """Raised when the clipboard cannot be read on this platform."""


def _candidates() -> list:
    """Return ordered command candidates for the current platform."""
    if sys.platform == "darwin":
        return [["pbpaste"]]
    if sys.platform.startswith("win"):
        return [["powershell", "-noprofile", "-command", "Get-Clipboard"]]
    # Linux / other unix: prefer Wayland, then the common X11 tools.
    return [
        ["wl-paste", "--no-newline"],
        ["xclip", "-selection", "clipboard", "-o"],
        ["xsel", "--clipboard", "--output"],
    ]


def read_clipboard() -> str:
    """
    Read text from the system clipboard.

    Returns:
        The clipboard contents as a string.

    Raises:
        ClipboardError: if no working clipboard tool is available.
    """
    tried = []
    for cmd in _candidates():
        if shutil.which(cmd[0]) is None:
            tried.append(cmd[0])
            continue
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return out.decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, OSError):
            tried.append(cmd[0])
            continue

    hint = (
        " On Linux, install one of: wl-clipboard (wl-paste), xclip, or xsel."
        if not (sys.platform == "darwin" or sys.platform.startswith("win"))
        else ""
    )
    raise ClipboardError(
        "Could not read the clipboard (tried: "
        + (", ".join(tried) or "no known tools")
        + ")." + hint
    )
