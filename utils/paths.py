"""Filesystem locations and OS integration helpers."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "AladinMovieSplitter"


def app_data_dir() -> Path:
    """Per-user folder for settings and logs (created on demand)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    folder = base / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resource_path(relative: str) -> Path:
    """Locate bundled resources both from source and from a PyInstaller build."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


def app_dir() -> Path:
    """Folder that contains the running program (the EXE when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def open_folder(path: Path | str) -> bool:
    """Open a folder in the system file manager. Returns False on failure."""
    path = Path(path)
    if not path.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except OSError:
        return False
