"""Locate FFmpeg and FFprobe on this machine."""
from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

from core.models import FFmpegTools, ToolsMissingError
from utils.paths import app_dir, resource_path
from utils.proc import run_hidden

log = logging.getLogger("msp.ffmpeg")

INSTALL_HELP = (
    "Aladin Movie Splitter needs FFmpeg and FFprobe to read and split videos.\n\n"
    "Easiest way (Windows 10/11): open Command Prompt and run\n"
    "    winget install Gyan.FFmpeg\n"
    "then restart this app.\n\n"
    "Manual way:\n"
    "  1. Download a Windows build from https://www.gyan.dev/ffmpeg/builds/ (release essentials).\n"
    "  2. Extract it, e.g. to C:\\ffmpeg  (you should have C:\\ffmpeg\\bin\\ffmpeg.exe).\n"
    "  3. Add C:\\ffmpeg\\bin to your PATH, or pick ffmpeg.exe / ffprobe.exe in Settings.\n"
    "  4. You can also drop both .exe files next to this application."
)


def _exe(name: str) -> str:
    return name + (".exe" if sys.platform == "win32" else "")


def _candidate_dirs() -> list[Path]:
    dirs = [app_dir(), app_dir() / "ffmpeg", app_dir() / "bin", resource_path("ffmpeg")]
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        dirs += [
            Path("C:/ffmpeg/bin"), Path("C:/Program Files/ffmpeg/bin"), Path("C:/Program Files (x86)/ffmpeg/bin"),
            Path("C:/ProgramData/chocolatey/bin"), Path.home() / "scoop" / "shims",
        ]
        if local:
            dirs.append(Path(local) / "Microsoft" / "WinGet" / "Links")
    return dirs


def _verify(path: str) -> str | None:
    """Run ``<tool> -version``; return its first line, or None if it does not work."""
    try:
        proc = run_hidden([path, "-version"], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
    except (OSError, ValueError, Exception):  # noqa: BLE001 - any failure means "unusable"
        return None
    if proc.returncode != 0:
        return None
    lines = (proc.stdout or "").splitlines()
    return lines[0].strip() if lines else "unknown version"


def _find_one(name: str, override: str, sibling_dir: Path | None) -> tuple[str, str] | None:
    candidates: list[str] = []
    if override:
        candidates.append(override)
    exe = _exe(name)
    if sibling_dir is not None:
        candidates.append(str(sibling_dir / exe))
    for folder in _candidate_dirs():
        candidates.append(str(folder / exe))
    on_path = shutil.which(name)
    if on_path:
        candidates.append(on_path)
    seen: set[str] = set()
    for cand in candidates:
        if cand in seen or not Path(cand).is_file():
            continue
        seen.add(cand)
        version = _verify(cand)
        if version:
            return cand, version
    return None


def find_tools(ffmpeg_override: str = "", ffprobe_override: str = "") -> FFmpegTools:
    """Return working FFmpeg/FFprobe paths or raise :class:`ToolsMissingError`."""
    ffmpeg = _find_one("ffmpeg", ffmpeg_override, None)
    ffprobe = _find_one("ffprobe", ffprobe_override, Path(ffmpeg[0]).parent if ffmpeg else None)
    missing = [n for n, r in (("FFmpeg", ffmpeg), ("FFprobe", ffprobe)) if r is None]
    if missing:
        raise ToolsMissingError(f"{' and '.join(missing)} could not be found.\n\n{INSTALL_HELP}")
    log.info("Using %s (%s)", ffmpeg[0], ffmpeg[1])  # type: ignore[index]
    return FFmpegTools(ffmpeg=ffmpeg[0], ffprobe=ffprobe[0], version=ffmpeg[1])  # type: ignore[index]
