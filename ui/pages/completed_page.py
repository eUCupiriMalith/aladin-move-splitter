"""Completed Files: history of finished splits."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from ui.dialogs import confirm, copy_text
from ui.state import PAGE_VIDEO, AppState
from ui.widgets import Card, IconButton, IconLabel, ScrollPage, clear_layout, elide, make_label
from utils.paths import open_folder
from utils.timefmt import format_human


class CompletedPage(ScrollPage):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.add_header("Completed Files", "Every movie you have split successfully.")
        bar = QHBoxLayout()
        self.count = make_label("", "muted")
        bar.addWidget(self.count)
        bar.addStretch(1)
        clear = IconButton("Clear history", "trash", "danger", "danger")
        clear.clicked.connect(self._clear)
        bar.addWidget(clear)
        self.body.addLayout(bar)
        self.list_box = QVBoxLayout()
        self.list_box.setSpacing(12)
        self.body.addLayout(self.list_box)
        self.body.addStretch(1)
        state.historyChanged.connect(self.refresh)
        self.refresh()

    def _clear(self) -> None:
        if self.state.settings.get("history") and confirm(self, "Clear history?",
                                                         "Remove the list of completed splits? Your files are not deleted.",
                                                         "Clear", "Cancel"):
            self.state.settings.clear_history()
            self.refresh()

    def refresh(self) -> None:
        clear_layout(self.list_box)
        history = self.state.settings.get("history")
        self.count.setText(f"{len(history)} movie(s) split")
        if not history:
            empty = Card(orientation="h", spacing=14)
            empty.layout_.addWidget(IconLabel("layers", 28, "muted"))
            empty.layout_.addWidget(make_label("Nothing here yet. Finished splits will be listed here.", "muted", wrap=True), 1)
            go = IconButton("Split a movie", "video")
            go.clicked.connect(lambda: self.state.navigate.emit(PAGE_VIDEO))
            empty.layout_.addWidget(go)
            self.list_box.addWidget(empty)
            return
        for i, item in enumerate(history):
            folder = Path(item.get("folder", ""))
            card = Card(orientation="h", spacing=14, margins=(20, 16, 20, 16))
            card.layout_.addWidget(IconLabel("check", 28, "success"), 0, Qt.AlignmentFlag.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addWidget(make_label(elide(item.get("title", "Movie"), 60), "h2"))
            col.addWidget(make_label(f"{item.get('parts', 0)} parts  ·  {format_human(item.get('seconds', 0))}  ·  "
                                     f"{item.get('mode', 'Fast')} mode  ·  {item.get('date', '')}", "muted"))
            exists = folder.exists()
            col.addWidget(make_label(elide(str(folder), 70) + ("" if exists else "  (folder no longer exists)"),
                                     "mono" if exists else "warning"))
            card.layout_.addLayout(col, 1)
            op = IconButton("Open", "folder", size=16)
            op.setEnabled(exists)
            op.clicked.connect(lambda _=False, f=folder: open_folder(f))
            cp = IconButton("", "copy", "muted", "ghost", size=16)
            cp.setToolTip("Copy folder path")
            cp.clicked.connect(lambda _=False, f=folder: copy_text(str(f), "Folder path copied"))
            rm = IconButton("", "close", "muted", "ghost", size=14)
            rm.setToolTip("Remove from history")
            rm.clicked.connect(lambda _=False, n=i: (self.state.settings.remove_history(n), self.refresh()))
            for b in (op, cp, rm):
                card.layout_.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
            self.list_box.addWidget(card)
