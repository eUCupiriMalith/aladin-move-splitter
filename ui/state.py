"""Shared application state. Pages read from and write to this object and listen to its signals."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from core.ffmpeg_locator import find_tools
from core.models import SplitResult, ToolsMissingError, VideoInfo
from core.naming import sanitize_name
from ui import theme
from utils.settings import Settings
from workers.probe_worker import ProbeWorker

log = logging.getLogger("msp.state")

PAGE_DASHBOARD, PAGE_VIDEO, PAGE_SPLIT, PAGE_PROGRESS, PAGE_COMPLETED, PAGE_SETTINGS = range(6)


class AppState(QObject):
    videoChanged = Signal()
    loadingChanged = Signal(bool)
    loadFailed = Signal(str)
    splitSettingsChanged = Signal()
    toolsChanged = Signal()
    busyChanged = Signal(bool)
    historyChanged = Signal()
    recentChanged = Signal()
    navigate = Signal(int)
    startJob = Signal(object)
    themeChanged = Signal(str)

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.tools = None
        self.tools_error = ""
        self.video: VideoInfo | None = None
        self.thumbnail: QPixmap | None = None
        self.loading = False
        self.busy = False
        self.segment_seconds: int = max(1, int(settings.get("last_duration_seconds")))
        self.accurate: bool = settings.get("mode") == "accurate"
        self.out_root = Path(settings.get("output_dir"))
        self._token = 0
        self._workers: set[ProbeWorker] = set()
        self.detect_tools()

    # ---- FFmpeg -----------------------------------------------------------
    def detect_tools(self) -> None:
        try:
            self.tools = find_tools(self.settings.get("ffmpeg_path"), self.settings.get("ffprobe_path"))
            self.tools_error = ""
        except ToolsMissingError as exc:
            self.tools, self.tools_error = None, str(exc)
        self.toolsChanged.emit()

    # ---- video ------------------------------------------------------------
    def load_video(self, path: str | Path) -> None:
        if self.busy:
            self.loadFailed.emit("Please wait until the current split finishes (or cancel it) before changing the video.")
            return
        if self.tools is None:
            self.loadFailed.emit(self.tools_error or "FFmpeg was not found.")
            return
        path = Path(path)
        self._token += 1
        token = self._token
        self.settings.set("last_open_dir", str(path.parent))
        self.loading = True
        self.loadingChanged.emit(True)
        self.navigate.emit(PAGE_VIDEO)
        worker = ProbeWorker(self.tools, path, token, self)
        worker.loaded.connect(self._on_loaded)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda w=worker: self._reap(w))
        self._workers.add(worker)
        worker.start()

    def _reap(self, worker: ProbeWorker) -> None:
        worker.wait()
        self._workers.discard(worker)
        worker.deleteLater()

    def _on_loaded(self, token: int, info: VideoInfo, thumb: bytes | None) -> None:
        if token != self._token:
            return
        pixmap = QPixmap()
        if thumb:
            pixmap.loadFromData(thumb)
        self.video = info
        self.thumbnail = pixmap if not pixmap.isNull() else None
        self.loading = False
        self.settings.push_recent(str(info.path))
        self.loadingChanged.emit(False)
        self.recentChanged.emit()
        self.videoChanged.emit()
        self.splitSettingsChanged.emit()

    def _on_failed(self, token: int, message: str) -> None:
        if token != self._token:
            return
        self.loading = False
        self.loadingChanged.emit(False)
        self.loadFailed.emit(message)

    def clear_video(self) -> None:
        if self.busy:
            return
        self._token += 1                  # ignore any probe still running
        self.video, self.thumbnail, self.loading = None, None, False
        self.loadingChanged.emit(False)
        self.videoChanged.emit()
        self.splitSettingsChanged.emit()

    # ---- theme ------------------------------------------------------------
    def set_theme(self, mode: str) -> None:
        self.settings.set("theme", mode)
        theme.set_mode(mode)
        self.themeChanged.emit(mode)

    # ---- split settings ---------------------------------------------------
    def set_segment_seconds(self, seconds: int) -> None:
        self.segment_seconds = int(seconds)
        if seconds > 0:
            self.settings.set("last_duration_seconds", int(seconds))
        self.splitSettingsChanged.emit()

    def set_accurate(self, accurate: bool) -> None:
        self.accurate = accurate
        self.settings.set("mode", "accurate" if accurate else "fast")
        self.splitSettingsChanged.emit()

    def set_out_root(self, path: str | Path) -> None:
        self.out_root = Path(path)
        self.settings.set("output_dir", str(self.out_root))
        self.splitSettingsChanged.emit()

    def output_dir(self) -> Path | None:
        if self.video is None:
            return None
        return self.out_root / sanitize_name(self.video.stem)

    def reset_split_settings(self) -> None:
        self.segment_seconds = 600
        self.accurate = False
        self.settings.set("last_duration_seconds", 600, save=False)
        self.settings.set("mode", "fast")
        self.splitSettingsChanged.emit()

    # ---- job state --------------------------------------------------------
    def set_busy(self, busy: bool) -> None:
        if self.busy != busy:
            self.busy = busy
            self.busyChanged.emit(busy)

    def record_result(self, result: SplitResult) -> None:
        job = result.job
        self.settings.add_history({
            "title": job.info.filename,
            "folder": str(job.out_dir),
            "parts": len(result.parts),
            "seconds": round(result.elapsed, 1),
            "mode": "Accurate" if job.accurate else "Fast",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self.historyChanged.emit()
