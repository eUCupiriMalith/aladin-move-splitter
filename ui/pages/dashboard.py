"""Dashboard: welcome, statistics, quick start and recent files."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ui.dialogs import pick_video
from ui.state import PAGE_VIDEO, AppState
from ui.widgets import (Card, DropZone, IconButton, ResponsiveRow, ScrollPage, StatTile, clear_layout, elide,
                        make_label)
from utils.timefmt import human_size


class DashboardPage(ScrollPage):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state

        hero = Card("hero", margins=(32, 28, 32, 28), spacing=10)
        hero.layout_.addWidget(make_label("Aladin Movie Splitter", "hero-title"))
        hero.layout_.addWidget(make_label(
            "Cut long movies into clean, evenly sized parts. Fast, lossless and fully automatic, with an "
            "organised output folder for every film.", "hero", wrap=True))
        row = QHBoxLayout()
        pick = IconButton("Select a video", "video", "secondary", "hero")
        pick.setToolTip("Choose a video to split (Ctrl+O)")
        pick.clicked.connect(lambda: pick_video(self, state))
        row.addWidget(pick)
        row.addStretch(1)
        hero.layout_.addSpacing(6)
        hero.layout_.addLayout(row)
        self.body.addWidget(hero)

        tiles = ResponsiveRow(760, 14)
        self.t_movies = StatTile("video", "Movies split", "0")
        self.t_parts = StatTile("layers", "Parts created", "0")
        self.t_ffmpeg = StatTile("check", "FFmpeg", "-")
        for t in (self.t_movies, self.t_parts, self.t_ffmpeg):
            tiles.add(t)
        self.body.addWidget(tiles)

        cols = ResponsiveRow(820, 18)
        drop = DropZone("Drop a movie here", "or click to browse. MP4, MKV, AVI, MOV, WebM and more")
        drop.browse.connect(lambda: pick_video(self, state))
        cols.add(drop, 3)

        recent = Card(spacing=8)
        head = QHBoxLayout()
        head.addWidget(make_label("Recent files", "h2"))
        head.addStretch(1)
        clear = IconButton("Clear", "trash", "muted", "ghost", size=16)
        clear.setToolTip("Forget the list of recent files")
        clear.clicked.connect(lambda: (state.settings.clear_recent(), self.refresh_recent()))
        head.addWidget(clear)
        recent.layout_.addLayout(head)
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(4)
        recent.layout_.addLayout(self.recent_box)
        recent.layout_.addStretch(1)
        cols.add(recent, 2)
        self.body.addWidget(cols)

        how = Card(spacing=6)
        how.layout_.addWidget(make_label("How it works", "h2"))
        for n, text in enumerate([
                "Select or drop a movie. Metadata and a thumbnail load instantly.",
                "Choose how long each part should be: type a time or use a preset.",
                "Press Start. Parts are saved in a folder named after the movie, e.g. Avatar_Part_001.mkv.",
        ], 1):
            how.layout_.addWidget(make_label(f"{n}.  {text}", "muted", wrap=True))
        self.body.addWidget(how)
        credit = make_label("Developed by Aladin", "caption")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(credit)
        self.body.addStretch(1)

        state.historyChanged.connect(self.refresh_stats)
        state.toolsChanged.connect(self.refresh_stats)
        state.recentChanged.connect(self.refresh_recent)
        self.refresh_stats()
        self.refresh_recent()

    def refresh_stats(self) -> None:
        history = self.state.settings.get("history")
        self.t_movies.set_value(str(len(history)))
        self.t_parts.set_value(str(sum(int(h.get("parts", 0)) for h in history)))
        self.t_ffmpeg.set_value("Ready" if self.state.tools else "Missing")

    def refresh_recent(self) -> None:
        clear_layout(self.recent_box)
        recent = self.state.settings.get("recent_files")
        if not recent:
            self.recent_box.addWidget(make_label("Videos you open will appear here.", "muted"))
            return
        for path in recent[:6]:
            p = Path(path)
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 2, 0, 2)
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(make_label(elide(p.name, 40), "h2"))
            size = human_size(p.stat().st_size) if p.exists() else "file not found"
            col.addWidget(make_label(f"{size}  ·  {elide(str(p.parent), 40)}", "caption"))
            h.addLayout(col, 1)
            open_btn = IconButton("Open", "play", "primary", "ghost", size=14)
            open_btn.setToolTip(f"Load {p.name}")
            open_btn.clicked.connect(lambda _=False, q=path: self.state.load_video(q))
            rm = IconButton("", "close", "muted", "ghost", size=14)
            rm.setToolTip("Remove from recent files")
            rm.clicked.connect(lambda _=False, q=path: (self.state.settings.remove_recent(q), self.refresh_recent()))
            h.addWidget(open_btn)
            h.addWidget(rm)
            self.recent_box.addWidget(row)
