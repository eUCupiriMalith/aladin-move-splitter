"""Output folder and part-file naming rules."""
from __future__ import annotations

import re
from pathlib import Path

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

# Container extensions the segment muxer can write, mapped to FFmpeg format names.
SEGMENT_FORMATS = {
    ".mp4": "mp4", ".m4v": "mp4", ".mov": "mov", ".mkv": "matroska", ".webm": "webm",
    ".avi": "avi", ".ts": "mpegts", ".flv": "flv", ".wmv": "asf", ".mpg": "mpeg", ".mpeg": "mpeg",
}
FALLBACK_EXTENSION = ".mkv"


def sanitize_name(name: str) -> str:
    """Make ``name`` safe to use as a Windows file/folder name."""
    cleaned = _INVALID.sub("_", name).strip().rstrip(". ")
    if not cleaned:
        cleaned = "movie"
    if cleaned.split(".")[0].upper() in _RESERVED:
        cleaned = "_" + cleaned
    return cleaned


def output_extension(source_ext: str) -> str:
    """Keep the original extension when we can write it, otherwise fall back to MKV."""
    ext = source_ext if source_ext.startswith(".") else "." + source_ext
    return ext if ext.lower() in SEGMENT_FORMATS else FALLBACK_EXTENSION


def part_filename(stem: str, index: int, ext: str) -> str:
    """``Avatar_Part_001.mkv`` - three digits minimum, growing past 999 naturally."""
    return f"{stem}_Part_{index:03d}{ext}"


def segment_pattern(stem: str, ext: str) -> str:
    """printf-style pattern for FFmpeg's segment muxer (literal ``%`` is escaped)."""
    return f"{stem.replace('%', '%%')}_Part_%03d{ext}"


def part_regex(stem: str, ext: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(stem)}_Part_(\d{{3,}}){re.escape(ext)}$", re.IGNORECASE)


def find_existing_parts(folder: Path, stem: str, ext: str) -> list[Path]:
    """Existing part files in ``folder`` ordered by part number."""
    if not folder.is_dir():
        return []
    pattern = part_regex(stem, ext)
    found = []
    for entry in folder.iterdir():
        match = pattern.match(entry.name)
        if match and entry.is_file():
            found.append((int(match.group(1)), entry))
    return [p for _, p in sorted(found)]


def output_dir_for(root: Path, stem: str) -> Path:
    return Path(root) / stem


def unique_output_dir(root: Path, stem: str) -> Path:
    """First of ``Avatar``, ``Avatar (2)``, ``Avatar (3)`` ... that does not exist yet."""
    candidate = Path(root) / stem
    n = 2
    while candidate.exists():
        candidate = Path(root) / f"{stem} ({n})"
        n += 1
    return candidate
