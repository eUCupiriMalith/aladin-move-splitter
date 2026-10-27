"""Settings: appearance, defaults, FFmpeg, data and keyboard shortcuts."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit

from ui import theme
from ui.dialogs import FFmpegSetupDialog, confirm, pick_folder
from ui.state import AppState
from ui.widgets import Card, IconButton, ScrollPage, make_label
from utils.logger import log_file_path
from utils.paths import open_folder

SHORTCUTS = [
    ("Ctrl+O", "Open a video"), ("Ctrl+1 … Ctrl+6", "Go to Dashboard … Settings"), ("Ctrl+Enter", "Start splitting"),
    ("Esc", "Cancel the running split"), ("Ctrl+T", "Toggle dark / light theme"), ("Ctrl+R", "Reset: clear video and settings"),
    ("Ctrl+Shift+C", "Copy the output folder path"), ("Ctrl+Shift+O", "Open the output folder"),
]


class SettingsPage(ScrollPage):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        st = state.settings
        self.add_header("Settings", "Make Aladin Movie Splitter work the way you like.")

        # appearance
        card = Card(spacing=12)
        card.layout_.addWidget(make_label("Appearance", "h2"))
        row = QHBoxLayout()
        self.dark_btn, self.light_btn = IconButton("Dark", "moon"), IconButton("Light", "sun")
        for b, mode in ((self.dark_btn, "dark"), (self.light_btn, "light")):
            b.setProperty("variant", "chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, m=mode: state.set_theme(m))
            row.addWidget(b)
        row.addStretch(1)
        card.layout_.addLayout(row)
        self.body.addWidget(card)
        state.themeChanged.connect(self._sync_theme)
        self._sync_theme()

        # defaults
        card = Card(spacing=10)
        card.layout_.addWidget(make_label("Defaults", "h2"))
        card.layout_.addWidget(make_label("DEFAULT OUTPUT FOLDER", "caption"))
        row = QHBoxLayout()
        self.out_edit = QLineEdit(str(state.out_root))
        self.out_edit.setReadOnly(True)
        pick = IconButton("Browse…", "folder")
        pick.clicked.connect(self._pick_out)
        row.addWidget(self.out_edit, 1)
        row.addWidget(pick)
        card.layout_.addLayout(row)
        self.chk_open = QCheckBox("Open the output folder after a successful split")
        self.chk_open.setChecked(bool(st.get("open_folder_after")))
        self.chk_open.toggled.connect(lambda v: st.set("open_folder_after", bool(v)))
        self.chk_confirm = QCheckBox("Ask for confirmation before starting a split")
        self.chk_confirm.setChecked(bool(st.get("confirm_before_start")))
        self.chk_confirm.toggled.connect(lambda v: st.set("confirm_before_start", bool(v)))
        card.layout_.addWidget(self.chk_open)
        card.layout_.addWidget(self.chk_confirm)
        self.body.addWidget(card)
        state.splitSettingsChanged.connect(lambda: self.out_edit.setText(str(state.out_root)))

        # ffmpeg
        card = Card(spacing=10)
        card.layout_.addWidget(make_label("FFmpeg", "h2"))
        self.ff_status = make_label("", "muted", wrap=True)
        card.layout_.addWidget(self.ff_status)
        self.ff_edit, self.fp_edit = QLineEdit(st.get("ffmpeg_path")), QLineEdit(st.get("ffprobe_path"))
        for edit, caption, hint in ((self.ff_edit, "FFMPEG PATH (optional)", "ffmpeg"), (self.fp_edit, "FFPROBE PATH (optional)", "ffprobe")):
            edit.setPlaceholderText(f"Leave empty to detect {hint} automatically")
            card.layout_.addWidget(make_label(caption, "caption"))
            r = QHBoxLayout()
            r.addWidget(edit, 1)
            b = IconButton("Browse…", "folder")
            b.clicked.connect(lambda _=False, e=edit: self._pick_exe(e))
            r.addWidget(b)
            card.layout_.addLayout(r)
        btns = QHBoxLayout()
        redetect = IconButton("Save && re-detect", "refresh")
        redetect.clicked.connect(self._redetect)
        help_btn = IconButton("Installation help", "gear")
        help_btn.clicked.connect(lambda: FFmpegSetupDialog(self.window(), state).exec())
        btns.addWidget(redetect)
        btns.addWidget(help_btn)
        btns.addStretch(1)
        card.layout_.addLayout(btns)
        self.body.addWidget(card)
        state.toolsChanged.connect(self._sync_tools)
        self._sync_tools()

        # data
        card = Card(spacing=10)
        card.layout_.addWidget(make_label("Data & troubleshooting", "h2"))
        row = QHBoxLayout()
        clear_recent = IconButton("Clear recent files", "trash")
        clear_recent.clicked.connect(lambda: (st.clear_recent(), state.recentChanged.emit()))
        log_btn = IconButton("Open log folder", "folder")
        log_btn.clicked.connect(lambda: open_folder(log_file_path().parent))
        reset = IconButton("Reset all settings", "refresh", "danger", "danger")
        reset.clicked.connect(self._reset_all)
        for b in (clear_recent, log_btn, reset):
            row.addWidget(b)
        row.addStretch(1)
        card.layout_.addLayout(row)
        card.layout_.addWidget(make_label(f"Log file: {log_file_path()}", "caption", wrap=True))
        self.body.addWidget(card)

        # shortcuts
        card = Card(spacing=8)
        card.layout_.addWidget(make_label("Keyboard shortcuts", "h2"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)
        for i, (keys, what) in enumerate(SHORTCUTS):
            grid.addWidget(make_label(keys, "mono"), i, 0)
            grid.addWidget(make_label(what, "muted"), i, 1)
        grid.setColumnStretch(1, 1)
        card.layout_.addLayout(grid)
        self.body.addWidget(card)
        card = Card(spacing=6)
        card.layout_.addWidget(make_label("About", "h2"))
        card.layout_.addWidget(make_label("Aladin Movie Splitter  ·  version 1.0.0", None))
        card.layout_.addWidget(make_label("Developed by Aladin", "muted"))
        self.body.addWidget(card)
        self.body.addStretch(1)

    def _sync_theme(self, *_args) -> None:
        self.dark_btn.setChecked(theme.mode() == "dark")
        self.light_btn.setChecked(theme.mode() == "light")

    def _sync_tools(self) -> None:
        t = self.state.tools
        self.ff_status.setText(f"Ready: {t.version}\n{t.ffmpeg}\n{t.ffprobe}" if t else "FFmpeg / FFprobe were not found. See installation help.")

    def _pick_out(self) -> None:
        folder = pick_folder(self, str(self.state.out_root))
        if folder:
            self.state.set_out_root(folder)

    def _pick_exe(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select executable", str(Path.home()), "Executables (*.exe);;All files (*.*)")
        if path:
            edit.setText(path)

    def _redetect(self) -> None:
        self.state.settings.set("ffmpeg_path", self.ff_edit.text().strip(), save=False)
        self.state.settings.set("ffprobe_path", self.fp_edit.text().strip())
        self.state.detect_tools()

    def _reset_all(self) -> None:
        if self.state.busy:
            return
        if confirm(self, "Reset all settings?", "This restores every setting to its default and clears recent files "
                   "and history. Your video files are not touched.", "Reset", "Cancel"):
            self.state.settings.reset()
            self.state.set_theme("dark")
            self.state.segment_seconds, self.state.accurate = 600, False
            self.state.out_root = Path(self.state.settings.get("output_dir"))
            self.chk_open.setChecked(True)
            self.chk_confirm.setChecked(True)
            self.ff_edit.clear()
            self.fp_edit.clear()
            self.state.detect_tools()
            self.state.splitSettingsChanged.emit()
            self.state.historyChanged.emit()
            self.state.recentChanged.emit()
