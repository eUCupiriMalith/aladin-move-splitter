"""Disk space helpers."""
from __future__ import annotations

import shutil
from pathlib import Path


def free_space(path: Path | str) -> int | None:
    """Free bytes on the drive that holds ``path`` (or its nearest existing parent)."""
    p = Path(path)
    for candidate in [p, *p.parents]:
        if candidate.exists():
            try:
                return shutil.disk_usage(candidate).free
            except OSError:
                return None
    return None
