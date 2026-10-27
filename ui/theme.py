"""Design system: colour tokens, dark/light palettes and the global stylesheet."""
from __future__ import annotations

from string import Template

from PySide6.QtCore import QObject, Signal

PALETTES: dict[str, dict[str, str]] = {
    "dark": dict(bg="#0E1220", surface="#161B2E", surface2="#1D2440", sidebar="#0A0E1A", border="#2A3358",
                 text="#E8ECFF", muted="#8E99C2", primary="#4F8CFF", secondary="#8B5CF6", accent="#22D3EE",
                 success="#34D399", warning="#FBBF24", danger="#F87171", input="#11162A", hover="#252D50",
                 white="#FFFFFF"),
    "light": dict(bg="#F3F5FC", surface="#FFFFFF", surface2="#EEF1FB", sidebar="#FFFFFF", border="#DDE2F3",
                  text="#1B2140", muted="#6B7399", primary="#3B76F0", secondary="#7C4DEB", accent="#0EA5C6",
                  success="#10B981", warning="#D99A06", danger="#E5484D", input="#F7F8FE", hover="#E6EAF8",
                  white="#FFFFFF"),
}


class _ThemeBus(QObject):
    changed = Signal()


bus = _ThemeBus()
_mode = "dark"
check_png = ""          # path of the checkbox tick image, set at start-up


def set_mode(mode: str) -> None:
    global _mode
    _mode = mode if mode in PALETTES else "dark"
    bus.changed.emit()


def mode() -> str:
    return _mode


def colors() -> dict[str, str]:
    return PALETTES[_mode]


def c(name: str) -> str:
    return PALETTES[_mode][name]


_QSS = Template("""
* { font-family: "Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px; color: $text; }
QWidget { background: transparent; }
QMainWindow, QWidget#root { background: $bg; }
QDialog, QMessageBox, QFileDialog { background: $surface; }
QToolTip { background: $surface2; color: $text; border: 1px solid $border; border-radius: 6px; padding: 6px 8px; }

QFrame#sidebar { background: $sidebar; border-right: 1px solid $border; }
QPushButton#navButton { text-align: left; padding: 11px 14px; border-radius: 12px; color: $muted;
    font-weight: 600; border: none; background: transparent; }
QPushButton#navButton:hover { background: $hover; color: $text; }
QPushButton#navButton:checked { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $primary, stop:1 $secondary); color: $white; }

QFrame[card="true"] { background: $surface; border: 1px solid $border; border-radius: 16px; }
QFrame[card="hero"] { border: none; border-radius: 20px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 $primary, stop:0.55 $secondary, stop:1 $accent); }
QFrame[card="banner"] { background: $surface2; border: 1px solid $warning; border-radius: 14px; }
QFrame[dropzone="true"] { background: $surface; border: 2px dashed $border; border-radius: 18px; }
QFrame[dropzone="true"]:hover { border-color: $primary; background: $surface2; }
QFrame#dropOverlay { background: rgba(79,140,255,0.22); border: 3px dashed $primary; border-radius: 20px; }
QFrame[divider="true"] { background: $border; max-height: 1px; border: none; }

QLabel[role="title"] { font-size: 26px; font-weight: 700; }
QLabel[role="h2"] { font-size: 16px; font-weight: 600; }
QLabel[role="muted"] { color: $muted; }
QLabel[role="caption"] { color: $muted; font-size: 11px; font-weight: 600; }
QLabel[role="stat"] { font-size: 24px; font-weight: 700; }
QLabel[role="mono"] { font-family: "Cascadia Mono", Consolas, "Courier New", monospace; color: $accent; }
QLabel[role="error"] { color: $danger; font-weight: 600; }
QLabel[role="warning"] { color: $warning; font-weight: 600; }
QLabel[role="success"] { color: $success; font-weight: 600; }
QLabel[role="hero"] { color: $white; }
QLabel[role="hero-title"] { color: $white; font-size: 28px; font-weight: 700; }

QPushButton { background: $surface2; border: 1px solid $border; border-radius: 10px; padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: $hover; border-color: $primary; }
QPushButton:pressed { background: $border; }
QPushButton:disabled { color: $muted; border-color: $border; background: $surface; }
QPushButton[variant="primary"] { border: none; color: $white; padding: 12px 24px; font-size: 14px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $primary, stop:0.6 $secondary, stop:1 $accent); }
QPushButton[variant="primary"]:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $accent, stop:0.5 $primary, stop:1 $secondary); }
QPushButton[variant="primary"]:disabled { background: $surface2; color: $muted; }
QPushButton[variant="danger"] { background: transparent; border: 1px solid $danger; color: $danger; }
QPushButton[variant="danger"]:hover { background: $danger; color: $white; }
QPushButton[variant="ghost"] { background: transparent; border: none; color: $muted; padding: 6px 10px; }
QPushButton[variant="ghost"]:hover { background: $hover; color: $text; }
QPushButton[variant="hero"] { background: $white; color: #3B2FCB; border: none; padding: 11px 22px; }
QPushButton[variant="hero"]:hover { background: #EDEBFF; }
QPushButton[variant="chip"] { border-radius: 12px; padding: 7px 16px; }
QPushButton[variant="chip"]:checked { border: none; color: $white;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 $primary, stop:1 $secondary); }
QPushButton[stepper="true"] { border-radius: 10px; padding: 0; font-size: 18px; min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; }

QLineEdit { background: $input; border: 1px solid $border; border-radius: 10px; padding: 8px 12px;
    selection-background-color: $primary; selection-color: $white; }
QLineEdit:focus { border: 1px solid $primary; }
QLineEdit:read-only { color: $muted; }
QLineEdit#timeEdit { font-size: 24px; font-weight: 700; padding: 6px 2px; }

QCheckBox, QRadioButton { spacing: 10px; background: transparent; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid $border; background: $input; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: $primary; }
QCheckBox::indicator:checked { background: $primary; border-color: $primary; image: url("$check"); }
QRadioButton::indicator { width: 18px; height: 18px; border-radius: 10px; border: 1px solid $border; background: $input; }
QRadioButton::indicator:checked { border-color: $primary;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 $primary, stop:0.45 $primary, stop:0.5 $input, stop:1 $input); }

QPlainTextEdit { background: $input; border: 1px solid $border; border-radius: 12px; padding: 8px;
    font-family: "Cascadia Mono", Consolas, "Courier New", monospace; font-size: 12px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $border; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { background: none; border: none; width: 0; height: 0; }
""")


def build_stylesheet() -> str:
    tokens = dict(colors())
    tokens["check"] = check_png.replace("\\", "/")
    return _QSS.safe_substitute(tokens)
