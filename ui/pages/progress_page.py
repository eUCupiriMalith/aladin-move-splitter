"""Processing Progress: live progress, success / failure / cancelled screens and the FFmpeg log."""
from __future__ import annotations

import logging
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPlainTextEdit, QStackedWidget, QVBoxLayout, QWidget

from core.models import SplitJob, SplitResult
from core.splitter import ProgressInfo
from ui.dialogs import confirm, copy_text
from ui.state import PAGE_SPLIT, PAGE_VIDEO, AppState
from ui.widgets import (Card, GradientProgressBar, IconButton, IconLabel, ScrollPage, Spinner, StatTile, elide,
                        make_label)
from utils.paths import open_folder
from utils.timefmt import format_hms, format_human, human_size
from workers.split_worker import SplitWorker

log = logging.getLogger("msp.progress_page")
IDLE, RUNNING, DONE, FAILED = range(4)


class ProgressPage(ScrollPage):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.worker: SplitWorker | None = None
        self.job: SplitJob | None = None
        self._t0 = 0.0
        self._verifying = False
        self.add_header("Processing Progress", "Watch your movie being split in real time.")
        self.views = QStackedWidget()
        self.body.addWidget(self.views)
        self.views.addWidget(self._build_idle())
        self.views.addWidget(self._build_running())
        self.views.addWidget(self._build_done())
        self.views.addWidget(self._build_failed())

        # log (shared by every view)
        self.log_card = Card(spacing=8)
        head = QHBoxLayout()
        head.addWidget(make_label("Processing log", "h2"))
        head.addStretch(1)
        self.copy_log = IconButton("Copy", "copy", "muted", "ghost", size=14)
        self.copy_log.clicked.connect(lambda: copy_text(self.log_view.toPlainText(), "Log copied"))
        self.toggle_log = IconButton("Show", None, None, "ghost")
        self.toggle_log.clicked.connect(lambda: self._show_log(not self.log_view.isVisible()))
        head.addWidget(self.copy_log)
        head.addWidget(self.toggle_log)
        self.log_card.layout_.addLayout(head)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(3000)
        self.log_view.setMinimumHeight(220)
        self.log_view.hide()
        self.log_card.layout_.addWidget(self.log_view)
        self.log_card.hide()
        self.body.addWidget(self.log_card)
        self.body.addStretch(1)

        self.clock = QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self._tick)
        state.startJob.connect(self.start_job)

    # ------------------------------------------------------------------ views
    def _build_idle(self) -> QWidget:
        card = Card(orientation="h", spacing=14)
        card.layout_.addWidget(IconLabel("activity", 28, "muted"))
        card.layout_.addWidget(make_label("Nothing is being processed. Choose a video and start a split to see progress here.", "muted", wrap=True), 1)
        go = IconButton("Split Settings", "sliders")
        go.clicked.connect(lambda: self.state.navigate.emit(PAGE_SPLIT))
        card.layout_.addWidget(go)
        return card

    def _build_running(self) -> QWidget:
        card = Card(spacing=16, margins=(26, 24, 26, 24))
        top = QHBoxLayout()
        top.setSpacing(14)
        self.spinner = Spinner(34)
        top.addWidget(self.spinner)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title_label = make_label("Preparing…", "h2")
        self.status_label = make_label("", "muted")
        col.addWidget(self.title_label)
        col.addWidget(self.status_label)
        top.addLayout(col, 1)
        self.percent_label = make_label("0%", "title")
        top.addWidget(self.percent_label)
        card.layout_.addLayout(top)
        self.bar = GradientProgressBar(18)
        card.layout_.addWidget(self.bar)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.t_part = StatTile("layers", "Current part", "-")
        self.t_elapsed = StatTile("clock", "Elapsed", "00:00:00")
        self.t_remaining = StatTile("clock", "Remaining", "-")
        self.t_speed = StatTile("activity", "Speed", "-")
        self.t_done = StatTile("check", "Completed parts", "0")
        self.t_failed = StatTile("error", "Failed parts", "0")
        for i, tile in enumerate((self.t_part, self.t_elapsed, self.t_remaining, self.t_speed, self.t_done, self.t_failed)):
            grid.addWidget(tile, i // 3, i % 3)
        card.layout_.addLayout(grid)
        row = QHBoxLayout()
        self.cancel_btn = IconButton("Cancel", "stop", "danger", "danger")
        self.cancel_btn.setToolTip("Stop splitting (Esc)")
        self.cancel_btn.clicked.connect(self.request_cancel)
        row.addStretch(1)
        row.addWidget(self.cancel_btn)
        card.layout_.addLayout(row)
        return card

    def _build_done(self) -> QWidget:
        card = Card(spacing=14, margins=(30, 30, 30, 30))
        card.layout_.addWidget(IconLabel("check", 72, "success"), 0, Qt.AlignmentFlag.AlignHCenter)
        t = make_label("Split complete!", "title")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.layout_.addWidget(t)
        self.done_sub = make_label("", "muted", wrap=True)
        self.done_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.layout_.addWidget(self.done_sub)
        tiles = QHBoxLayout()
        self.d_parts, self.d_time, self.d_mode = (StatTile("layers", "Total parts", "0"), StatTile("clock", "Processing time", "-"),
                                                  StatTile("gear", "Mode", "-"))
        for tile in (self.d_parts, self.d_time, self.d_mode):
            tiles.addWidget(tile)
        card.layout_.addLayout(tiles)
        card.layout_.addWidget(make_label("OUTPUT FOLDER", "caption"))
        self.d_folder = make_label("", "mono", wrap=True)
        self.d_folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card.layout_.addWidget(self.d_folder)
        self.d_notes = make_label("", "warning", wrap=True)
        card.layout_.addWidget(self.d_notes)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.open_btn = IconButton("Open Folder", "folder", "white", "primary")
        self.open_btn.clicked.connect(self._open_out)
        copy = IconButton("Copy path", "copy")
        copy.clicked.connect(lambda: copy_text(str(self.job.out_dir) if self.job else "", "Output folder path copied"))
        another = IconButton("Split Another Movie", "video")
        another.clicked.connect(self._another)
        row.addStretch(1)
        for b in (self.open_btn, copy, another):
            row.addWidget(b)
        row.addStretch(1)
        card.layout_.addLayout(row)
        return card

    def _build_failed(self) -> QWidget:
        card = Card(spacing=14, margins=(30, 30, 30, 30))
        self.f_icon = IconLabel("error", 72, "danger")
        card.layout_.addWidget(self.f_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        self.f_title = make_label("Split failed", "title")
        self.f_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.layout_.addWidget(self.f_title)
        self.f_msg = make_label("", None, wrap=True)
        self.f_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.f_msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card.layout_.addWidget(self.f_msg)
        row = QHBoxLayout()
        back = IconButton("Back to Split Settings", "sliders", "white", "primary")
        back.clicked.connect(lambda: self.state.navigate.emit(PAGE_SPLIT))
        self.f_folder = IconButton("Open folder", "folder")
        self.f_folder.clicked.connect(self._open_out)
        row.addStretch(1)
        row.addWidget(back)
        row.addWidget(self.f_folder)
        row.addStretch(1)
        card.layout_.addLayout(row)
        return card

    # ------------------------------------------------------------------ job lifecycle
    def start_job(self, job: SplitJob) -> None:
        if self.worker is not None:
            return
        tools = self.state.tools
        if tools is None:
            return
        self.job = job
        self._verifying = False
        self.log_view.clear()
        self.log_card.show()
        self._show_log(False)
        self.title_label.setText(f"Splitting {elide(job.info.filename, 48)}")
        self.status_label.setText("Starting FFmpeg…")
        self.percent_label.setText("0%")
        self.bar.setValue(0, animate=False)
        self.bar.setActive(True)
        self.spinner.start()
        self.cancel_btn.setEnabled(True)
        for tile, text in ((self.t_part, f"1 / {job.expected_parts}"), (self.t_elapsed, "00:00:00"), (self.t_remaining, "calculating…"),
                           (self.t_speed, "-"), (self.t_done, "0"), (self.t_failed, "0")):
            tile.set_value(text)
        self.views.setCurrentIndex(RUNNING)
        self._t0 = time.monotonic()
        self.clock.start()
        self.state.set_busy(True)

        w = SplitWorker(tools, job, self)
        w.progress.connect(self._on_progress)
        w.status.connect(self._on_status)
        w.log_line.connect(self.log_view.appendPlainText)
        w.succeeded.connect(self._on_success)
        w.failed.connect(self._on_failed)
        w.cancelled.connect(self._on_cancelled)
        w.finished.connect(self._reap)
        self.worker = w
        w.start()

    def _reap(self) -> None:
        w, self.worker = self.worker, None
        if w is not None:
            w.wait()
            w.deleteLater()

    def _tick(self) -> None:
        self.t_elapsed.set_value(format_hms(time.monotonic() - self._t0))

    def _on_progress(self, p: ProgressInfo) -> None:
        self.bar.setValue(p.percent)
        self.percent_label.setText(f"{p.percent:.0f}%")
        self.t_part.set_value(f"{p.current_part} / {p.total_parts}")
        self.t_remaining.set_value(format_hms(p.eta) if p.eta is not None else "calculating…")
        self.t_speed.set_value(p.speed or "-")
        self.t_done.set_value(str(p.completed_parts))
        if not self._verifying:
            self.status_label.setText(f"Splitting part {p.current_part} of {p.total_parts}")

    def _on_status(self, text: str) -> None:
        self._verifying = text.startswith("Verif")
        self.status_label.setText(text)
        if self._verifying:
            self.t_remaining.set_value("almost done")

    def _finish_common(self) -> None:
        self.clock.stop()
        self.spinner.stop()
        self.bar.setActive(False)
        self.state.set_busy(False)

    def _on_success(self, result: SplitResult) -> None:
        self._finish_common()
        self.state.record_result(result)
        job = result.job
        self.done_sub.setText(f"“{job.info.filename}” was split into {len(result.parts)} verified part(s).")
        self.d_parts.set_value(str(len(result.parts)))
        self.d_time.set_value(format_human(result.elapsed))
        self.d_mode.set_value("Accurate" if job.accurate else "Fast")
        self.d_folder.setText(str(job.out_dir))
        self.d_notes.setText("\n".join(result.warnings + result.notes))
        self.d_notes.setVisible(bool(result.warnings or result.notes))
        self.views.setCurrentIndex(DONE)
        if self.state.settings.get("open_folder_after"):
            open_folder(job.out_dir)

    def _on_failed(self, message: str, failed_parts: int) -> None:
        self._finish_common()
        self.t_failed.set_value(str(failed_parts))
        self.f_icon.set_icon("error", "danger")
        self.f_title.setText("Split failed")
        self.f_msg.setText(f"{message}\n\nFailed parts: {failed_parts}. The movie was NOT marked as completed.")
        self.f_folder.setVisible(bool(self.job and self.job.out_dir.exists()))
        self.views.setCurrentIndex(FAILED)
        self._show_log(True)

    def _on_cancelled(self) -> None:
        self._finish_common()
        self.f_icon.set_icon("alert", "warning")
        self.f_title.setText("Split cancelled")
        self.f_msg.setText("Splitting was cancelled and the partial files were removed.")
        self.f_folder.hide()
        self.views.setCurrentIndex(FAILED)

    # ------------------------------------------------------------------ user actions
    def request_cancel(self) -> None:
        if self.worker is None or self.views.currentIndex() != RUNNING or not self.cancel_btn.isEnabled():
            return
        if confirm(self, "Cancel splitting?", "Stop now? Parts created so far will be deleted.",
                   "Yes, cancel", "Keep going"):
            if self.worker is not None:
                self.cancel_btn.setEnabled(False)
                self.status_label.setText("Cancelling…")
                self.worker.cancel()

    def _open_out(self) -> None:
        if self.job:
            open_folder(self.job.out_dir)

    def _another(self) -> None:
        self.state.clear_video()
        self.views.setCurrentIndex(IDLE)
        self.state.navigate.emit(PAGE_VIDEO)

    def _show_log(self, visible: bool) -> None:
        self.log_view.setVisible(visible)
        self.toggle_log.setText("Hide" if visible else "Show")

    def shutdown(self) -> None:
        """Called when the window closes: stop FFmpeg and wait for the thread."""
        w = self.worker
        if w is not None:
            w.cancel()
            w.wait(20000)
