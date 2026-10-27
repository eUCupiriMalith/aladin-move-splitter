"""Aladin Movie Splitter - entry point (developed by Aladin)."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _install_excepthook(logger) -> None:
    def hook(exc_type, exc, tb) -> None:
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Unexpected error",
                                 "Something went wrong:\n\n" + "".join(traceback.format_exception_only(exc_type, exc)) +
                                 "\nDetails were written to the log file (Settings > Open log folder).")
        except Exception:  # noqa: BLE001
            pass
    sys.excepthook = hook


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from ui import icons, theme
    from ui.main_window import APP_NAME, MainWindow
    from ui.state import AppState
    from utils.logger import setup_logging
    from utils.settings import Settings

    logger = setup_logging()
    _install_excepthook(logger)
    if sys.platform == "win32":
        try:  # gives the taskbar the right icon/grouping
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AladinMovieSplitter.App")
        except Exception:  # noqa: BLE001
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("AladinMovieSplitter")
    theme.check_png = icons.ensure_check_png()

    settings = Settings()
    theme.set_mode(settings.get("theme"))
    state = AppState(settings)
    window = MainWindow(state)
    window.show()

    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():     # "Open with" / drag onto the EXE
        state.load_video(sys.argv[1])
    logger.info("Aladin Movie Splitter started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
