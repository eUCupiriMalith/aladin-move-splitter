"""Video Selection: choose a file and inspect its metadata."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui import icons, theme
from ui.dialogs import FFmpegSetupDialog, pick_video
from ui.state import PAGE_SPLIT, AppState
from ui.widgets import (Card, DropZone, IconButton, IconLabel, ResponsiveRow, ScrollPage, Spinner, clear_layout,
                        make_label, rounded_pixmap)
from utils.timefmt import format_hms, human_size


class VideoPage(ScrollPage):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.add_header("Video Selection", "Choose the movie you want to split. You can also drag a file anywhere into this window.")

        # error card
        self.error_card = Card(orientation="h", spacing=12)
        self.error_card.layout_.addWidget(IconLabel("alert", 24, "danger"), 0, Qt.AlignmentFlag.AlignTop)
        self.error_label = make_label("", "error", wrap=True)
        self.error_card.layout_.addWidget(self.error_label, 1)
        self.setup_btn = IconButton("FFmpeg setup", "gear")
        self.setup_btn.clicked.connect(lambda: FFmpegSetupDialog(self.window(), state).exec())
        self.error_card.layout_.addWidget(self.setup_btn, 0, Qt.AlignmentFlag.AlignTop)
        self.error_card.hide()
        self.body.addWidget(self.error_card)

        # empty state
        self.empty = DropZone("Drop a video here", "MP4, MKV, AVI, MOV, WebM and more  ·  Ctrl+O to browse")
        self.empty.browse.connect(lambda: pick_video(self, state))
        self.body.addWidget(self.empty)

        # loading state
        self.loading = Card(orientation="h", margins=(26, 26, 26, 26), spacing=16)
        self.spinner = Spinner(36)
        self.loading.layout_.addWidget(self.spinner)
        self.loading.layout_.addWidget(make_label("Reading video information…", "h2"), 1)
        self.loading.hide()
        self.body.addWidget(self.loading)

        # loaded state
        self.loaded = QWidget()
        lv = QVBoxLayout(self.loaded)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(16)
        row = ResponsiveRow(780, 18)
        left = Card(spacing=12)
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setMinimumHeight(190)
        left.layout_.addWidget(self.thumb)
        btns = QHBoxLayout()
        replace = IconButton("Replace", "refresh")
        replace.setToolTip("Choose a different video (Ctrl+O)")
        replace.clicked.connect(lambda: pick_video(self, state))
        self.remove_btn = IconButton("Remove", "trash", "danger", "danger")
        self.remove_btn.setToolTip("Clear the selected video")
        self.remove_btn.clicked.connect(state.clear_video)
        btns.addWidget(replace)
        btns.addWidget(self.remove_btn)
        left.layout_.addLayout(btns)
        row.add(left, 4)

        right = Card(spacing=10)
        right.layout_.addWidget(make_label("Video details", "h2"))
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(8)
        self.grid.setColumnStretch(1, 1)
        right.layout_.addLayout(self.grid)
        right.layout_.addStretch(1)
        row.add(right, 5)
        lv.addWidget(row)
        go = IconButton("Continue to Split Settings", "sliders", "white", "primary")
        go.clicked.connect(lambda: state.navigate.emit(PAGE_SPLIT))
        lv.addWidget(go, 0, Qt.AlignmentFlag.AlignRight)
        self.loaded.hide()
        self.body.addWidget(self.loaded)
        self.body.addStretch(1)

        state.videoChanged.connect(self.refresh)
        state.loadingChanged.connect(self._on_loading)
        state.loadFailed.connect(self._on_error)
        state.busyChanged.connect(lambda busy: self.remove_btn.setEnabled(not busy))
        state.toolsChanged.connect(self.refresh)
        theme.bus.changed.connect(self.refresh)
        self.refresh()

    def _on_loading(self, loading: bool) -> None:
        if loading:
            self.error_card.hide()
        self.refresh()

    def _on_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.setup_btn.setVisible(self.state.tools is None)
        self.error_card.show()
        self.refresh()

    def refresh(self) -> None:
        s = self.state
        loading, video = s.loading, s.video
        self.empty.setVisible(video is None and not loading)
        self.loading.setVisible(loading)
        if loading:
            self.spinner.start()
        else:
            self.spinner.stop()
        self.loaded.setVisible(video is not None and not loading)
        if video is None or loading:
            return
        self.error_card.hide()
        if s.thumbnail:
            self.thumb.setPixmap(rounded_pixmap(s.thumbnail, QSize(480, 270), 14))
        else:
            self.thumb.setPixmap(icons.pixmap("video", theme.c("muted"), 64))
        audio = ", ".join(f"{a.codec_name.upper()}" + (f" {a.channels}ch" if a.channels else "") +
                          (f" ({a.language})" if a.language else "") for a in video.audio_streams) or "None"
        subs = ", ".join(sorted({x.language or x.codec_name for x in video.subtitle_streams})) or "None"
        rows = [
            ("Filename", video.filename), ("Folder", str(video.path.parent)), ("File size", human_size(video.size_bytes)),
            ("Format", video.format_long or video.format_name), ("Resolution", video.resolution),
            ("Duration", f"{format_hms(video.duration)}"), ("Frame rate", f"{video.fps:.2f} fps" if video.fps else "Unknown"),
            ("Video codec", video.video_codec.upper()), ("Audio", audio), ("Subtitles", subs),
            ("Bitrate", f"{video.bit_rate / 1_000_000:.2f} Mb/s" if video.bit_rate else "Unknown"),
        ]
        clear_layout(self.grid)
        for i, (k, v) in enumerate(rows):
            self.grid.addWidget(make_label(k.upper(), "caption"), i, 0, Qt.AlignmentFlag.AlignTop)
            val = make_label(v, None, wrap=True)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.grid.addWidget(val, i, 1)
