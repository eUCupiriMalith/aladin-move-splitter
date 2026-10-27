"""QThread wrapper around the split engine."""
from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from core.models import FFmpegTools, SplitCancelled, SplitError, SplitJob
from core.splitter import SplitEngine

log = logging.getLogger("msp.worker")


class SplitWorker(QThread):
    progress = Signal(object)        # core.splitter.ProgressInfo
    status = Signal(str)
    log_line = Signal(str)
    succeeded = Signal(object)       # core.models.SplitResult
    failed = Signal(str, int)        # message, failed part count
    cancelled = Signal()

    def __init__(self, tools: FFmpegTools, job: SplitJob, parent=None) -> None:
        super().__init__(parent)
        self.engine = SplitEngine(tools, job, on_progress=self.progress.emit,
                                  on_status=self.status.emit, on_log=self.log_line.emit)

    def cancel(self) -> None:
        self.engine.cancel()

    def run(self) -> None:  # executes in the worker thread
        try:
            result = self.engine.run()
        except SplitCancelled:
            self.cancelled.emit()
        except SplitError as exc:
            log.error("Split failed: %s", exc)
            self.failed.emit(str(exc), exc.failed_parts)
        except Exception as exc:  # noqa: BLE001 - never let a worker thread die silently
            log.exception("Unexpected error in split worker")
            self.failed.emit(f"Unexpected error: {exc}", 1)
        else:
            self.succeeded.emit(result)
