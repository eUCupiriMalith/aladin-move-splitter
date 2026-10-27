"""Reusable, theme-aware widgets that make up the design system."""
from __future__ import annotations

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QIntValidator, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QLineEdit, QVBoxLayout, QWidget)

from ui import icons, theme


# ---------------------------------------------------------------- helpers
def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def elide(text: str, limit: int = 56) -> str:
    """Shorten long paths in the middle so they fit on one line."""
    if len(text) <= limit:
        return text
    head = limit // 2 - 1
    return text[:head] + "…" + text[-(limit - head - 1):]


def make_label(text: str = "", role: str | None = None, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    label.setWordWrap(wrap)
    return label


def set_role(label: QLabel, role: str | None) -> None:
    label.setProperty("role", role or "")
    repolish(label)


def clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def rounded_pixmap(source: QPixmap, size: QSize, radius: int = 14) -> QPixmap:
    scaled = source.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size.width(), size.height()), radius, radius)
    p.setClipPath(path)
    p.drawPixmap((size.width() - scaled.width()) // 2, (size.height() - scaled.height()) // 2, scaled)
    p.end()
    return out


# ---------------------------------------------------------------- containers
class Card(QFrame):
    """Rounded surface. kind: 'true' (normal), 'hero' (gradient) or 'banner' (warning)."""

    def __init__(self, kind: str = "true", orientation: str = "v", margins=(22, 20, 22, 20), spacing: int = 12) -> None:
        super().__init__()
        self.setProperty("card", kind)
        self.layout_ = QVBoxLayout(self) if orientation == "v" else QHBoxLayout(self)
        self.layout_.setContentsMargins(*margins)
        self.layout_.setSpacing(spacing)


class ScrollPage(QWidget):
    """Base page: a vertically scrolling body so small windows stay usable."""

    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(32, 28, 32, 28)
        self.body.setSpacing(18)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)

    def add_header(self, title: str, subtitle: str = "") -> None:
        self.body.addWidget(make_label(title, "title"))
        if subtitle:
            self.body.addWidget(make_label(subtitle, "muted", wrap=True))


class ResponsiveRow(QWidget):
    """Lays children out side by side, switching to a column when the window is narrow."""

    def __init__(self, threshold: int = 900, spacing: int = 18) -> None:
        super().__init__()
        self._threshold = threshold
        self._box = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(spacing)

    def add(self, widget: QWidget, stretch: int = 1) -> None:
        self._box.addWidget(widget, stretch)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        direction = (QBoxLayout.Direction.LeftToRight if event.size().width() >= self._threshold
                     else QBoxLayout.Direction.TopToBottom)
        if self._box.direction() != direction:
            self._box.setDirection(direction)
        super().resizeEvent(event)


# ---------------------------------------------------------------- icon widgets
class IconLabel(QLabel):
    def __init__(self, name: str, size: int = 22, color: str = "text") -> None:
        super().__init__()
        self._name, self._size, self._color = name, size, color
        self.setFixedSize(size, size)
        theme.bus.changed.connect(self.refresh)
        self.refresh()

    def set_icon(self, name: str, color: str | None = None) -> None:
        self._name = name
        if color:
            self._color = color
        self.refresh()

    def refresh(self) -> None:
        self.setPixmap(icons.pixmap(self._name, theme.c(self._color), self._size))


class IconButton(QPushButton):
    def __init__(self, text: str = "", icon_name: str | None = None, color: str = "text", variant: str | None = None,
                 checked_color: str | None = None, size: int = 18, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._icon_name, self._color, self._checked_color, self._isize = icon_name, color, checked_color, size
        if variant:
            self.setProperty("variant", variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        theme.bus.changed.connect(self._refresh_icon)
        self._refresh_icon()

    def set_icon_name(self, name: str) -> None:
        self._icon_name = name
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        if not self._icon_name:
            return
        checked = theme.c(self._checked_color) if self._checked_color else None
        self.setIcon(icons.icon(self._icon_name, theme.c(self._color), self._isize, checked))
        self.setIconSize(QSize(self._isize, self._isize))


class StatTile(Card):
    def __init__(self, icon_name: str, caption: str, value: str = "-") -> None:
        super().__init__(orientation="h", margins=(18, 16, 18, 16), spacing=14)
        self.layout_.addWidget(IconLabel(icon_name, 28, "accent"))
        col = QVBoxLayout()
        col.setSpacing(0)
        self.value_label = make_label(value, "stat")
        col.addWidget(self.value_label)
        col.addWidget(make_label(caption.upper(), "caption"))
        self.layout_.addLayout(col, 1)

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


# ---------------------------------------------------------------- animated widgets
class Spinner(QWidget):
    """Comet-style loading indicator."""

    def __init__(self, size: int = 30) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        theme.bus.changed.connect(self.update)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)
        p.setPen(QPen(QColor(theme.c("border")), 3))
        p.drawEllipse(rect)
        if self._timer.isActive():
            grad = QConicalGradient(rect.center(), -self._angle)
            grad.setColorAt(0.0, QColor(theme.c("accent")))
            grad.setColorAt(0.35, QColor(theme.c("secondary")))
            tail = QColor(theme.c("primary"))
            tail.setAlpha(0)
            grad.setColorAt(0.7, tail)
            grad.setColorAt(1.0, tail)
            pen = QPen(QBrush(grad), 3.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawEllipse(rect)


class GradientProgressBar(QWidget):
    """Rounded gradient bar with eased value changes and a moving shimmer while active."""

    def __init__(self, height: int = 16) -> None:
        super().__init__()
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._display = 0.0
        self._shimmer = 0.0
        self._anim = QPropertyAnimation(self, b"displayValue", self)
        self._anim.setDuration(380)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)
        theme.bus.changed.connect(self.update)

    def _get(self) -> float:
        return self._display

    def _set(self, value: float) -> None:
        self._display = value
        self.update()

    displayValue = Property(float, _get, _set)

    def setValue(self, value: float, animate: bool = True) -> None:  # noqa: N802
        value = max(0.0, min(100.0, value))
        self._anim.stop()
        if animate:
            self._anim.setStartValue(self._display)
            self._anim.setEndValue(value)
            self._anim.start()
        else:
            self._set(value)

    def value(self) -> float:
        return self._display

    def setActive(self, active: bool) -> None:  # noqa: N802
        if active:
            self._timer.start()
        else:
            self._timer.stop()
            self.update()

    def _tick(self) -> None:
        self._shimmer = (self._shimmer + 0.02) % 1.6
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        r = h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.c("surface2")))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        if self._display <= 0:
            return
        fill_w = max(h, w * self._display / 100.0)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, fill_w, h), r, r)
        p.setClipPath(clip)
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(theme.c("primary")))
        grad.setColorAt(0.55, QColor(theme.c("secondary")))
        grad.setColorAt(1.0, QColor(theme.c("accent")))
        p.fillRect(QRectF(0, 0, fill_w, h), QBrush(grad))
        if self._timer.isActive():
            x = (self._shimmer - 0.3) * fill_w
            shine = QLinearGradient(x, 0, x + fill_w * 0.3, 0)
            transparent = QColor(255, 255, 255, 0)
            shine.setColorAt(0.0, transparent)
            shine.setColorAt(0.5, QColor(255, 255, 255, 70))
            shine.setColorAt(1.0, transparent)
            p.fillRect(QRectF(0, 0, fill_w, h), QBrush(shine))


# ---------------------------------------------------------------- input widgets
class DurationField(QWidget):
    """A labelled number box with - / + buttons (used for hours, minutes, seconds)."""

    valueChanged = Signal(int)  # noqa: N815

    def __init__(self, label: str, maximum: int) -> None:
        super().__init__()
        self._max = maximum
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)
        col.addWidget(make_label(label.upper(), "caption"), 0, Qt.AlignmentFlag.AlignHCenter)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.edit = QLineEdit("0")
        self.edit.setObjectName("timeEdit")
        self.edit.setValidator(QIntValidator(0, maximum, self))
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit.setMinimumWidth(64)
        self.edit.setMaxLength(len(str(maximum)))
        self.edit.setToolTip(f"{label} (0 - {maximum})")
        self.edit.textEdited.connect(lambda _t: self.valueChanged.emit(self.value()))
        self.edit.editingFinished.connect(lambda: self.setValue(self.value()))
        minus, plus = QPushButton("−"), QPushButton("+")
        for btn, step in ((minus, -1), (plus, 1)):
            btn.setProperty("stepper", True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setAutoRepeat(True)
            btn.clicked.connect(lambda _=False, s=step: self.setValue(self.value() + s, notify=True))
        minus.setToolTip(f"Decrease {label.lower()}")
        plus.setToolTip(f"Increase {label.lower()}")
        row.addWidget(minus)
        row.addWidget(self.edit, 1)
        row.addWidget(plus)
        col.addLayout(row)

    def value(self) -> int:
        try:
            return max(0, min(self._max, int(self.edit.text() or 0)))
        except ValueError:
            return 0

    def setValue(self, value: int, notify: bool = False) -> None:  # noqa: N802
        value = max(0, min(self._max, int(value)))
        changed = self.edit.text() != str(value)
        self.edit.setText(str(value))
        if notify and changed:
            self.valueChanged.emit(value)


class DropZone(QFrame):
    """Big clickable area inviting the user to drop or browse for a video."""

    browse = Signal()

    def __init__(self, title: str = "Drop a video here", subtitle: str = "MP4, MKV, AVI, MOV, WebM and more") -> None:
        super().__init__()
        self.setProperty("dropzone", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(230)
        col = QVBoxLayout(self)
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.setSpacing(10)
        icon = IconLabel("upload", 44, "primary")
        col.addWidget(icon, 0, Qt.AlignmentFlag.AlignHCenter)
        t = make_label(title, "h2")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(t)
        s = make_label(subtitle, "muted")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(s)
        btn = IconButton("Browse files…", "folder", "white", "primary")
        btn.setToolTip("Choose a video file (Ctrl+O)")
        btn.clicked.connect(self.browse)
        col.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.browse.emit()
        super().mousePressEvent(event)
