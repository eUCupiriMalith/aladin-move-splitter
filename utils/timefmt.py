"""Formatting and parsing helpers for durations and file sizes."""
from __future__ import annotations

import math


def _safe_seconds(seconds: float | None) -> int:
    if seconds is None or (isinstance(seconds, float) and (math.isnan(seconds) or math.isinf(seconds))):
        return 0
    return max(0, int(round(seconds)))


def format_hms(seconds: float | None) -> str:
    """Return ``HH:MM:SS`` (hours expand beyond two digits when needed)."""
    total = _safe_seconds(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_human(seconds: float | None) -> str:
    """Return a compact human string such as ``2h 10m 05s``."""
    total = _safe_seconds(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def hms_to_seconds(hours: int, minutes: int, seconds: int) -> int:
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def split_hms(total_seconds: float) -> tuple[int, int, int]:
    total = _safe_seconds(total_seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return h, m, s


def human_size(num_bytes: float | None) -> str:
    if not num_bytes or num_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"
