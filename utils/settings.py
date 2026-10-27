"""JSON-backed user settings, recent files and job history."""
from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from typing import Any

from utils.paths import app_data_dir

log = logging.getLogger("msp.settings")

MAX_RECENT = 10
MAX_HISTORY = 100

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "output_dir": str(Path.home() / "Videos" / "Split Movies"),
    "last_duration_seconds": 600,
    "mode": "fast",                 # "fast" (stream copy) or "accurate" (re-encode)
    "open_folder_after": True,
    "confirm_before_start": True,
    "ffmpeg_path": "",
    "ffprobe_path": "",
    "last_open_dir": "",
    "recent_files": [],
    "history": [],
}


class Settings:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (app_data_dir() / "settings.json")
        self.data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self.load()

    # -- persistence ---------------------------------------------------
    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("Could not read settings (%s); using defaults", exc)
            return
        if isinstance(raw, dict):
            for key in DEFAULTS:
                if key in raw and type(raw[key]) is type(DEFAULTS[key]):
                    self.data[key] = raw[key]

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("Could not save settings: %s", exc)

    # -- access --------------------------------------------------------
    def get(self, key: str) -> Any:
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any, save: bool = True) -> None:
        self.data[key] = value
        if save:
            self.save()

    def reset(self) -> None:
        self.data = copy.deepcopy(DEFAULTS)
        self.save()

    # -- recent files --------------------------------------------------
    def push_recent(self, path: str) -> None:
        items = [p for p in self.data["recent_files"] if p != path]
        items.insert(0, path)
        self.set("recent_files", items[:MAX_RECENT])

    def remove_recent(self, path: str) -> None:
        self.set("recent_files", [p for p in self.data["recent_files"] if p != path])

    def clear_recent(self) -> None:
        self.set("recent_files", [])

    # -- history -------------------------------------------------------
    def add_history(self, entry: dict[str, Any]) -> None:
        items = [entry, *self.data["history"]]
        self.set("history", items[:MAX_HISTORY])

    def remove_history(self, index: int) -> None:
        items = list(self.data["history"])
        if 0 <= index < len(items):
            del items[index]
            self.set("history", items)

    def clear_history(self) -> None:
        self.set("history", [])
