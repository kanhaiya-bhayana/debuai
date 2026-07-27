"""
Tests for debugai/clipboard.py — cross-platform clipboard reading.
Subprocess and platform detection are mocked; no real clipboard is touched.
"""
import subprocess

import pytest

import debugai.clipboard as clipboard
from debugai.clipboard import read_clipboard, ClipboardError


# ── platform selection ────────────────────────────────────────────────────────

class TestCandidates:

    def test_macos_uses_pbpaste(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "darwin")
        assert clipboard._candidates() == [["pbpaste"]]

    def test_windows_uses_powershell(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "win32")
        cmds = clipboard._candidates()
        assert cmds[0][0] == "powershell"
        assert "Get-Clipboard" in cmds[0]

    def test_linux_prefers_wayland_then_x11(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "linux")
        first = [c[0] for c in clipboard._candidates()]
        assert first == ["wl-paste", "xclip", "xsel"]


# ── read_clipboard ────────────────────────────────────────────────────────────

class TestReadClipboard:

    def test_reads_from_first_available_tool(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "darwin")
        monkeypatch.setattr(clipboard.shutil, "which", lambda name: "/usr/bin/" + name)
        monkeypatch.setattr(
            clipboard.subprocess, "check_output",
            lambda cmd, stderr=None: b"pasted log text",
        )
        assert read_clipboard() == "pasted log text"

    def test_decodes_invalid_utf8_without_crashing(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "darwin")
        monkeypatch.setattr(clipboard.shutil, "which", lambda name: "/usr/bin/" + name)
        monkeypatch.setattr(
            clipboard.subprocess, "check_output",
            lambda cmd, stderr=None: b"\xff\xfeboom",
        )
        # errors="replace" — must not raise
        assert "boom" in read_clipboard()

    def test_falls_back_to_next_tool_when_first_missing(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "linux")
        # Only xclip is installed; wl-paste is absent.
        monkeypatch.setattr(
            clipboard.shutil, "which",
            lambda name: "/usr/bin/xclip" if name == "xclip" else None,
        )
        used = []

        def fake_check_output(cmd, stderr=None):
            used.append(cmd[0])
            return b"from xclip"

        monkeypatch.setattr(clipboard.subprocess, "check_output", fake_check_output)
        assert read_clipboard() == "from xclip"
        assert used == ["xclip"]  # wl-paste skipped, xsel never reached

    def test_raises_when_no_tool_available(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "linux")
        monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)
        with pytest.raises(ClipboardError):
            read_clipboard()

    def test_linux_error_message_mentions_install_hint(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "linux")
        monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)
        with pytest.raises(ClipboardError) as exc:
            read_clipboard()
        assert "xclip" in str(exc.value)

    def test_raises_when_tool_present_but_fails(self, monkeypatch):
        monkeypatch.setattr(clipboard.sys, "platform", "darwin")
        monkeypatch.setattr(clipboard.shutil, "which", lambda name: "/usr/bin/pbpaste")

        def boom(cmd, stderr=None):
            raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(clipboard.subprocess, "check_output", boom)
        with pytest.raises(ClipboardError):
            read_clipboard()
