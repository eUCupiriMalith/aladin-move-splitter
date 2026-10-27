"""Vector icons drawn with QPainter (no image files needed, recoloured per theme)."""
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap)

from ui import theme
from utils.paths import app_data_dir


def _pt(*pairs):
    return [QPointF(x, y) for x, y in pairs]


def _home(p, col):
    p.drawPolyline(_pt((3, 11), (12, 3), (21, 11)))
    p.drawRoundedRect(QRectF(5.5, 10, 13, 10.5), 2, 2)
    p.drawLine(QPointF(10, 20.5), QPointF(10, 15))
    p.drawLine(QPointF(14, 20.5), QPointF(14, 15))


def _video(p, col):
    p.drawRoundedRect(QRectF(3, 5.5, 18, 13), 3, 3)
    p.setBrush(col)
    p.drawPolygon(_pt((10.5, 9.3), (15.2, 12), (10.5, 14.7)))


def _sliders(p, col):
    p.setBrush(col)
    for y, x in ((6, 8), (12, 16), (18, 10)):
        p.drawLine(QPointF(3, y), QPointF(21, y))
        p.drawEllipse(QPointF(x, y), 2.4, 2.4)


def _activity(p, col):
    p.drawPolyline(_pt((2.5, 12), (7, 12), (10, 4.5), (14, 19.5), (17, 12), (21.5, 12)))


def _check(p, col):
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawPolyline(_pt((7.5, 12.5), (10.8, 15.8), (16.5, 9)))


def _tick(p, col):
    p.drawPolyline(_pt((5, 12.5), (10, 17.5), (19, 7)))


def _gear(p, col):
    p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
    p.drawEllipse(QPointF(12, 12), 7.2, 7.2)
    for angle in range(0, 360, 45):
        p.save()
        p.translate(12, 12)
        p.rotate(angle)
        p.drawLine(QPointF(0, -7.2), QPointF(0, -10))
        p.restore()


def _sun(p, col):
    p.drawEllipse(QPointF(12, 12), 4.2, 4.2)
    for angle in range(0, 360, 45):
        p.save()
        p.translate(12, 12)
        p.rotate(angle)
        p.drawLine(QPointF(0, -7), QPointF(0, -9.5))
        p.restore()


def _moon(p, col):
    outer = QPainterPath()
    outer.addEllipse(QPointF(12, 12), 8.5, 8.5)
    cut = QPainterPath()
    cut.addEllipse(QPointF(17, 8), 7, 7)
    p.setBrush(col)
    p.drawPath(outer.subtracted(cut))


def _folder(p, col):
    p.drawRoundedRect(QRectF(3, 8, 18, 11.5), 2, 2)
    p.drawPolyline(_pt((3, 8), (3, 6), (9, 6), (11, 8)))


def _copy(p, col):
    p.drawRoundedRect(QRectF(9, 9, 12, 12), 2.5, 2.5)
    p.drawPolyline(_pt((15, 5), (15, 4.5), (5.5, 4.5), (4, 6), (4, 15.5), (5.5, 16), (6.5, 16)))


def _trash(p, col):
    p.drawLine(QPointF(4, 7), QPointF(20, 7))
    p.drawPolyline(_pt((9, 7), (9, 4), (15, 4), (15, 7)))
    p.drawRoundedRect(QRectF(6, 7, 12, 13.5), 2, 2)
    p.drawLine(QPointF(10, 11), QPointF(10, 16.5))
    p.drawLine(QPointF(14, 11), QPointF(14, 16.5))


def _refresh(p, col):
    p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 270 * 16)
    p.drawPolyline(_pt((19.5, 3), (19, 7.6), (14.4, 7.2)))


def _play(p, col):
    p.setBrush(col)
    p.drawPolygon(_pt((7.5, 5), (19, 12), (7.5, 19)))


def _stop(p, col):
    p.setBrush(col)
    p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)


def _close(p, col):
    p.drawLine(QPointF(6, 6), QPointF(18, 18))
    p.drawLine(QPointF(18, 6), QPointF(6, 18))


def _upload(p, col):
    p.drawLine(QPointF(12, 16), QPointF(12, 4.5))
    p.drawPolyline(_pt((7, 9), (12, 4), (17, 9)))
    p.drawPolyline(_pt((4, 15), (4, 20), (20, 20), (20, 15)))


def _alert(p, col):
    p.drawPolygon(_pt((12, 3.5), (21.5, 20), (2.5, 20)))
    p.drawLine(QPointF(12, 9.5), QPointF(12, 14.5))
    p.drawPoint(QPointF(12, 17.3))


def _cross_circle(p, col):
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawLine(QPointF(8.5, 8.5), QPointF(15.5, 15.5))
    p.drawLine(QPointF(15.5, 8.5), QPointF(8.5, 15.5))


def _clock(p, col):
    p.drawEllipse(QPointF(12, 12), 9, 9)
    p.drawPolyline(_pt((12, 6.5), (12, 12), (16, 14)))


def _layers(p, col):
    p.drawPolygon(_pt((12, 3.5), (21, 8.5), (12, 13.5), (3, 8.5)))
    p.drawPolyline(_pt((3, 12.5), (12, 17.5), (21, 12.5)))


_DRAW = {
    "home": _home, "video": _video, "sliders": _sliders, "activity": _activity, "check": _check, "tick": _tick,
    "gear": _gear, "sun": _sun, "moon": _moon, "folder": _folder, "copy": _copy, "trash": _trash,
    "refresh": _refresh, "play": _play, "stop": _stop, "close": _close, "upload": _upload, "alert": _alert,
    "error": _cross_circle, "clock": _clock, "layers": _layers,
}


def pixmap(name: str, color: str, size: int = 22, stroke: float = 2.0) -> QPixmap:
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 24, size / 24)
    col = QColor(color)
    pen = QPen(col, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _DRAW[name](p, col)
    p.end()
    return pm


def icon(name: str, color: str, size: int = 22, checked_color: str | None = None) -> QIcon:
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
    ic.addPixmap(pixmap(name, checked_color or color, size), QIcon.Mode.Normal, QIcon.State.On)
    return ic


def logo_pixmap(size: int = 64) -> QPixmap:
    """Gradient rounded square with a film glyph: used for the sidebar logo and window icon."""
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    pal = theme.PALETTES["dark"]
    grad.setColorAt(0.0, QColor(pal["primary"]))
    grad.setColorAt(0.55, QColor(pal["secondary"]))
    grad.setColorAt(1.0, QColor(pal["accent"]))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.26, size * 0.26)
    inner = int(size * 0.62)
    glyph = pixmap("video", "#FFFFFF", inner, stroke=2.2)
    p.drawPixmap(int((size - inner) / 2), int((size - inner) / 2), glyph)
    p.end()
    return pm


def ensure_check_png() -> str:
    """Write the white tick used by checked checkboxes; returns its path."""
    path = Path(app_data_dir()) / "check.png"
    pixmap("tick", "#FFFFFF", 16, stroke=2.4).save(str(path), "PNG")
    return str(path)
