"""Subprocess helpers that never flash a console window on Windows."""
from __future__ import annotations

import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def run_hidden(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)


def popen_hidden(cmd: list[str], **kwargs) -> subprocess.Popen:
    kwargs.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.Popen(cmd, **kwargs)
