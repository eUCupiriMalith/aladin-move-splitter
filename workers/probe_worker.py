"""Reads video metadata and a thumbnail without blocking the UI."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from core.models import FFmpegTools, MovieSplitterError
from core.probe import extract_thumbnail, probe_video

log = logging.getLogger("msp.probe")


class ProbeWorker(QThread):
    loaded = Signal(int, object, object)   # token, VideoInfo, thumbnail bytes | None
    failed = Signal(int, str)              # token, message

    def __init__(self, tools: FFmpegTools, path: Path, token: int, parent=None) -> None:
        super().__init__(parent)
        self._tools, self._path, self._token = tools, path, token

    def run(self) -> None:
        try:
            info = probe_video(self._tools, self._path)
            thumb = extract_thumbnail(self._tools, info)
        except MovieSplitterError as exc:
            self.failed.emit(self._token, str(exc))
        except Exception as exc:  # noqa: BLE001
            log.exception("Unexpected probe failure")
            self.failed.emit(self._token, f"Unexpected error while reading the file: {exc}")
        else:
            self.loaded.emit(self._token, info, thumb)
