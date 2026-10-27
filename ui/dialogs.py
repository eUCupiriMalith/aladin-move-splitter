"""Dialog helpers shared by the pages."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton,
                               QToolTip, QVBoxLayout, QWidget)

from core.ffmpeg_locator import INSTALL_HELP
from ui.state import AppState
from ui.widgets import IconButton, make_label

VIDEO_FILTER = ("Video files (*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.ts *.mpg *.mpeg *.wmv *.flv);;"
                "All files (*.*)")


def pick_video(parent: QWidget, state: AppState) -> None:
    start = state.settings.get("last_open_dir") or str(Path.home())
    path, _ = QFileDialog.getOpenFileName(parent, "Select a video", start, VIDEO_FILTER)
    if path:
        state.load_video(path)


def pick_folder(parent: QWidget, start: str) -> str:
    return QFileDialog.getExistingDirectory(parent, "Choose a folder", start if Path(start).exists() else str(Path.home()))


def confirm(parent: QWidget, title: str, text: str, yes: str = "Yes", no: str = "Cancel",
            icon: QMessageBox.Icon = QMessageBox.Icon.Question) -> bool:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    yes_btn = box.addButton(yes, QMessageBox.ButtonRole.AcceptRole)
    box.addButton(no, QMessageBox.ButtonRole.RejectRole)
    box.exec()
    return box.clickedButton() is yes_btn


def ask_overwrite(parent: QWidget, folder: Path, count: int) -> str:
    """Returns 'overwrite', 'new' or 'cancel'."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Files already exist")
    box.setText(f"{count} part file(s) from an earlier split already exist in:\n{folder}\n\n"
                "Aladin Movie Splitter never overwrites files without your permission.")
    over = box.addButton("Overwrite them", QMessageBox.ButtonRole.DestructiveRole)
    new = box.addButton("Use a new folder", QMessageBox.ButtonRole.AcceptRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.exec()
    clicked = box.clickedButton()
    return "overwrite" if clicked is over else "new" if clicked is new else "cancel"


def show_error(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)


def copy_text(text: str, message: str = "Copied to clipboard") -> None:
    QGuiApplication.clipboard().setText(text)
    QToolTip.showText(QCursor.pos(), message)


class FFmpegSetupDialog(QDialog):
    """Explains how to install FFmpeg and lets the user point to it manually."""

    def __init__(self, parent: QWidget, state: AppState) -> None:
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("FFmpeg setup")
        self.resize(640, 470)
        col = QVBoxLayout(self)
        col.setContentsMargins(22, 20, 22, 20)
        col.setSpacing(12)
        col.addWidget(make_label("FFmpeg setup", "h2"))
        self.status = make_label("", "muted", wrap=True)
        col.addWidget(self.status)
        text = QPlainTextEdit(INSTALL_HELP)
        text.setReadOnly(True)
        col.addWidget(text, 1)
        row = QHBoxLayout()
        pick = IconButton("Select ffmpeg.exe…", "folder")
        pick.clicked.connect(self._pick)
        recheck = IconButton("Re-check", "refresh")
        recheck.clicked.connect(self._recheck)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(pick)
        row.addWidget(recheck)
        row.addStretch(1)
        row.addWidget(close)
        col.addLayout(row)
        self._update_status()

    def _update_status(self) -> None:
        if self.state.tools:
            self.status.setText(f"FFmpeg is ready: {self.state.tools.version}")
        else:
            self.status.setText("FFmpeg / FFprobe were not found on this computer.")

    def _recheck(self) -> None:
        self.state.detect_tools()
        self._update_status()

    def _pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select ffmpeg.exe", str(Path.home()), "FFmpeg (ffmpeg*);;All files (*.*)")
        if path:
            self.state.settings.set("ffmpeg_path", path)
            sibling = Path(path).with_name("ffprobe" + Path(path).suffix)
            if sibling.is_file():
                self.state.settings.set("ffprobe_path", str(sibling))
            self._recheck()
