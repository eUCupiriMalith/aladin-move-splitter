"""Main window: sidebar navigation, page stack, drag-and-drop and shortcuts."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QMainWindow, QStackedWidget, QVBoxLayout, QWidget)

from ui import icons, theme
from ui.dialogs import FFmpegSetupDialog, confirm, copy_text, pick_video
from ui.pages.completed_page import CompletedPage
from ui.pages.dashboard import DashboardPage
from ui.pages.progress_page import ProgressPage
from ui.pages.settings_page import SettingsPage
from ui.pages.split_page import SplitPage
from ui.pages.video_page import VideoPage
from ui.state import (PAGE_COMPLETED, PAGE_DASHBOARD, PAGE_PROGRESS, PAGE_SETTINGS, PAGE_SPLIT, PAGE_VIDEO, AppState)
from ui.widgets import Card, IconButton, IconLabel, make_label
from utils.paths import open_folder

APP_NAME = "Aladin Movie Splitter"
APP_VERSION = "1.0.0"
NAV = [("Dashboard", "home"), ("Video Selection", "video"), ("Split Settings", "sliders"),
       ("Processing", "activity"), ("Completed Files", "check"), ("Settings", "gear")]


class MainWindow(QMainWindow):
    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(icons.logo_pixmap(128)))
        self.setMinimumSize(980, 660)
        self.resize(1200, 780)
        self.setAcceptDrops(True)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        self.banner = Card("banner", orientation="h", margins=(16, 10, 16, 10), spacing=12)
        self.banner.layout_.addWidget(IconLabel("alert", 22, "warning"))
        self.banner.layout_.addWidget(make_label("FFmpeg was not found. Videos cannot be read or split until it is installed.", None, wrap=True), 1)
        setup = IconButton("Setup help", "gear")
        setup.clicked.connect(lambda: FFmpegSetupDialog(self, state).exec())
        self.banner.layout_.addWidget(setup)
        banner_wrap = QWidget()
        bl = QVBoxLayout(banner_wrap)
        bl.setContentsMargins(24, 16, 24, 0)
        bl.addWidget(self.banner)
        self.banner_wrap = banner_wrap
        right.addWidget(banner_wrap)

        self.stack = QStackedWidget()
        self.dashboard, self.video_page, self.split_page = DashboardPage(state), VideoPage(state), SplitPage(state)
        self.progress_page, self.completed_page, self.settings_page = ProgressPage(state), CompletedPage(state), SettingsPage(state)
        for page in (self.dashboard, self.video_page, self.split_page, self.progress_page, self.completed_page, self.settings_page):
            self.stack.addWidget(page)
        right.addWidget(self.stack, 1)
        outer.addLayout(right, 1)

        self.overlay = QFrame(self.stack)
        self.overlay.setObjectName("dropOverlay")
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ol = QVBoxLayout(self.overlay)
        ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ol.addWidget(IconLabel("upload", 56, "primary"), 0, Qt.AlignmentFlag.AlignHCenter)
        ol.addWidget(make_label("Drop your video to load it", "title"), 0, Qt.AlignmentFlag.AlignHCenter)
        self.overlay.hide()

        self._fade: QPropertyAnimation | None = None
        state.navigate.connect(self.go)
        state.themeChanged.connect(lambda _m: self.apply_theme())
        state.toolsChanged.connect(self._sync_banner)
        state.busyChanged.connect(self._sync_busy)
        self._add_shortcuts()
        self._sync_banner()
        self.nav_buttons[PAGE_DASHBOARD].setChecked(True)
        self.apply_theme()
        self._sync_theme_button()

    # ------------------------------------------------------------------ layout
    def _build_sidebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(236)
        col = QVBoxLayout(bar)
        col.setContentsMargins(16, 22, 16, 16)
        col.setSpacing(6)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(40))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(make_label("Aladin", "h2"))
        names.addWidget(make_label("MOVIE SPLITTER", "caption"))
        brand.addLayout(names, 1)
        col.addLayout(brand)
        col.addSpacing(18)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[IconButton] = []
        for i, (label, icon_name) in enumerate(NAV):
            b = IconButton(f"  {label}", icon_name, "muted", checked_color="white", size=20)
            b.setObjectName("navButton")
            b.setCheckable(True)
            b.setToolTip(f"{label}  (Ctrl+{i + 1})")
            b.clicked.connect(lambda _=False, n=i: self.go(n))
            self.nav_group.addButton(b, i)
            self.nav_buttons.append(b)
            col.addWidget(b)
        col.addStretch(1)
        self.theme_btn = IconButton("  Light theme", "sun", "muted", "ghost")
        self.theme_btn.setToolTip("Toggle dark / light theme (Ctrl+T)")
        self.theme_btn.clicked.connect(self.toggle_theme)
        col.addWidget(self.theme_btn)
        col.addWidget(make_label("Developed by Aladin", "caption"))
        col.addWidget(make_label(f"v{APP_VERSION}", "caption"))
        return bar

    # ------------------------------------------------------------------ navigation & theme
    def go(self, index: int) -> None:
        if not 0 <= index < self.stack.count():
            return
        self.nav_buttons[index].setChecked(True)
        if index == self.stack.currentIndex():
            return
        page = self.stack.widget(index)
        self.stack.setCurrentIndex(index)
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda p=page: QTimer.singleShot(0, lambda: p.setGraphicsEffect(None)))
        self._fade = anim
        anim.start()

    def apply_theme(self) -> None:
        QApplication.instance().setStyleSheet(theme.build_stylesheet())
        self._sync_theme_button()

    def toggle_theme(self) -> None:
        self.state.set_theme("light" if theme.mode() == "dark" else "dark")

    def _sync_theme_button(self) -> None:
        dark = theme.mode() == "dark"
        self.theme_btn.setText("  Light theme" if dark else "  Dark theme")
        self.theme_btn.set_icon_name("sun" if dark else "moon")

    def _sync_banner(self) -> None:
        self.banner_wrap.setVisible(self.state.tools is None)

    def _sync_busy(self, busy: bool) -> None:
        self.setWindowTitle(f"{APP_NAME}  -  splitting…" if busy else APP_NAME)

    # ------------------------------------------------------------------ shortcuts
    def _add_shortcuts(self) -> None:
        def sc(keys: str, fn) -> None:
            QShortcut(QKeySequence(keys), self, activated=fn)
        sc("Ctrl+O", lambda: pick_video(self, self.state))
        for i in range(6):
            sc(f"Ctrl+{i + 1}", lambda n=i: self.go(n))
        sc("Ctrl+Return", self._start_shortcut)
        sc("Ctrl+Enter", self._start_shortcut)
        sc("Esc", self.progress_page.request_cancel)
        sc("Ctrl+T", self.toggle_theme)
        sc("Ctrl+R", self._reset_all)
        sc("Ctrl+Shift+C", self._copy_output)
        sc("Ctrl+Shift+O", self._open_output)

    def _start_shortcut(self) -> None:
        if self.stack.currentIndex() == PAGE_SPLIT:
            self.split_page.start()

    def _reset_all(self) -> None:
        if self.state.busy:
            return
        self.state.clear_video()
        self.state.reset_split_settings()
        self.go(PAGE_DASHBOARD)

    def _copy_output(self) -> None:
        folder = self.state.output_dir() or self.state.out_root
        copy_text(str(folder), "Output folder path copied")

    def _open_output(self) -> None:
        for candidate in (self.state.output_dir(), self.state.out_root):
            if candidate and Path(candidate).exists():
                open_folder(candidate)
                return

    # ------------------------------------------------------------------ drag & drop
    def _dropped_file(self, event) -> str | None:
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).is_file():
                return url.toLocalFile()
        return None

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls() and self._dropped_file(event):
            event.acceptProposedAction()
            self.overlay.setGeometry(self.stack.rect().adjusted(12, 12, -12, -12))
            self.overlay.raise_()
            self.overlay.show()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self.overlay.hide()
        event.accept()

    def dropEvent(self, event) -> None:  # noqa: N802
        self.overlay.hide()
        path = self._dropped_file(event)
        if path:
            event.acceptProposedAction()
            self.state.load_video(path)

    # ------------------------------------------------------------------ closing
    def closeEvent(self, event) -> None:  # noqa: N802
        if self.state.busy:
            if not confirm(self, "Split in progress", "A split is still running. Cancel it and exit?", "Cancel split and exit", "Keep running"):
                event.ignore()
                return
            self.progress_page.shutdown()
        for worker in list(self.state._workers):
            if not worker.wait(3000):
                worker.terminate()
                worker.wait(1000)
        event.accept()
