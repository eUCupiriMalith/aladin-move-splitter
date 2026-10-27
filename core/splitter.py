"""The split engine: runs FFmpeg, reports progress, verifies the result.

This module has no Qt dependency; workers/split_worker.py wraps it in a QThread.
"""
from __future__ import annotations

import logging
import math
import re
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.command import build_split_command
from core.errors import explain_ffmpeg_error
from core.models import (FFmpegTools, PartResult, ProbeError, SplitCancelled, SplitError,
                         SplitJob, SplitResult)
from core.naming import find_existing_parts, part_regex
from core.planner import estimate_part_count
from core.probe import probe_duration
from utils.proc import popen_hidden

log = logging.getLogger("msp.engine")

_PROGRESS_KEYS = re.compile(
    r"^(frame|fps|stream_\d+_\d+_q|bitrate|total_size|out_time_us|out_time_ms|out_time|"
    r"dup_frames|drop_frames|speed|progress)=(.*)$")
_OPENING = re.compile(r"Opening '(.+?)' for writing")


@dataclass
class ProgressInfo:
    percent: float              # 0..100 of the movie processed
    current_part: int
    total_parts: int
    elapsed: float
    eta: float | None
    speed: str
    completed_parts: int
    failed_parts: int = 0


def _parse_clock(text: str) -> float | None:
    m = re.match(r"^(-?)(\d+):(\d+):(\d+(?:\.\d+)?)$", text.strip())
    if not m:
        return None
    seconds = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + float(m.group(4))
    return -seconds if m.group(1) else seconds


class SplitEngine:
    def __init__(self, tools: FFmpegTools, job: SplitJob,
                 on_progress: Callable[[ProgressInfo], None] | None = None,
                 on_status: Callable[[str], None] | None = None,
                 on_log: Callable[[str], None] | None = None) -> None:
        self.tools = tools
        self.job = job
        self._on_progress = on_progress or (lambda _p: None)
        self._on_status = on_status or (lambda _s: None)
        self._on_log = on_log or (lambda _l: None)
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._opened: list[Path] = []
        self._t0 = 0.0

    # -- public API --------------------------------------------------------
    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def cancel(self) -> None:
        """Thread-safe. Stops FFmpeg; run() then cleans up and raises SplitCancelled."""
        self._cancel.set()
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    def run(self) -> SplitResult:
        job = self.job
        self._t0 = time.monotonic()
        self._prepare_output()
        cmd, dropped = build_split_command(self.tools, job)
        self._log("Command: " + subprocess.list2cmdline(cmd))
        for item in dropped:
            self._log(f"Not copied: {item}")
        total_parts = job.expected_parts or estimate_part_count(job.info.duration, job.segment_seconds)
        self._status("Splitting…")

        try:
            proc = popen_hidden(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
        except OSError as exc:
            raise SplitError(f"Could not start FFmpeg: {exc}") from exc
        with self._lock:
            self._proc = proc
        if self._cancel.is_set():
            proc.terminate()

        tail: deque[str] = deque(maxlen=80)
        out_time = 0.0
        speed = ""
        have_us = False
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line:
                continue
            m = _PROGRESS_KEYS.match(line)
            if m:
                key, value = m.group(1), m.group(2)
                if key == "out_time_us":
                    try:
                        out_time = int(value) / 1_000_000
                        have_us = True
                    except ValueError:
                        pass
                elif key == "out_time" and not have_us:
                    parsed = _parse_clock(value)
                    if parsed is not None and parsed >= 0:
                        out_time = parsed
                elif key == "speed":
                    speed = value.strip()
                elif key == "progress":
                    self._emit_progress(out_time, speed, total_parts, finished=(value == "end"))
                continue
            tail.append(line)
            self._log(line)
            opening = _OPENING.search(line)
            if opening:
                self._opened.append(Path(opening.group(1)))

        return_code = proc.wait()
        with self._lock:
            self._proc = None

        if self._cancel.is_set():
            self._status("Cancelling… removing partial files")
            self._cleanup_after_cancel()
            raise SplitCancelled()
        if return_code != 0:
            self._remove_last_partial()
            raise SplitError(explain_ffmpeg_error(list(tail), return_code), failed_parts=1)
        return self._verify(total_parts)

    # -- internals ---------------------------------------------------------
    def _log(self, text: str) -> None:
        log.debug(text)
        self._on_log(text)

    def _status(self, text: str) -> None:
        self._on_status(text)

    def _prepare_output(self) -> None:
        job = self.job
        try:
            job.out_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            raise SplitError(f"No permission to create the output folder:\n{job.out_dir}") from exc
        except OSError as exc:
            raise SplitError(f"Could not create the output folder:\n{job.out_dir}\n{exc}") from exc
        existing = find_existing_parts(job.out_dir, job.stem, job.out_ext)
        if existing and not job.overwrite:
            raise SplitError("Part files from an earlier run already exist and overwriting was not confirmed.")
        for path in existing:                       # user explicitly confirmed overwrite
            try:
                path.unlink()
                self._log(f"Removed existing file (overwrite confirmed): {path.name}")
            except OSError as exc:
                raise SplitError(f"Could not replace existing file {path.name}: {exc}") from exc

    def _emit_progress(self, out_time: float, speed: str, total_parts: int, finished: bool) -> None:
        job = self.job
        elapsed = time.monotonic() - self._t0
        percent = 100.0 if finished else max(0.0, min(99.9, out_time / job.info.duration * 100))
        if self._opened:
            current = len(self._opened)
        else:
            current = int(out_time // job.segment_seconds) + 1
        current = max(1, min(current, max(total_parts, current)))
        completed = total_parts if finished else max(0, current - 1)
        eta = elapsed * (100 - percent) / percent if percent >= 1 and not finished else (0.0 if finished else None)
        self._on_progress(ProgressInfo(percent, current, max(total_parts, current), elapsed, eta,
                                       speed if speed and speed != "N/A" else "", completed))

    def _remove_last_partial(self) -> None:
        if self._opened:
            last = self._opened[-1]
            try:
                if last.exists():
                    last.unlink()
                    self._log(f"Removed incomplete file: {last.name}")
            except OSError as exc:
                self._log(f"Could not remove {last.name}: {exc}")

    def _cleanup_after_cancel(self) -> None:
        job = self.job
        for path in find_existing_parts(job.out_dir, job.stem, job.out_ext):
            try:
                path.unlink()
            except OSError as exc:
                self._log(f"Could not remove {path.name}: {exc}")
        try:
            job.out_dir.rmdir()              # only succeeds if the folder is now empty
        except OSError:
            pass

    def _verify(self, expected_parts: int) -> SplitResult:
        job = self.job
        self._status("Verifying output files…")
        paths = find_existing_parts(job.out_dir, job.stem, job.out_ext)
        if not paths:
            raise SplitError("FFmpeg finished, but no output files were created.")
        pattern = part_regex(job.stem, job.out_ext)
        results: list[PartResult] = []
        bad: list[str] = []
        for i, path in enumerate(paths, 1):
            if self._cancel.is_set():
                self._cleanup_after_cancel()
                raise SplitCancelled()
            self._status(f"Verifying part {i} of {len(paths)}…")
            try:
                size = path.stat().st_size
                if size <= 0:
                    raise ProbeError("file is empty")
                duration = probe_duration(self.tools, path)
                if duration <= 0:
                    raise ProbeError("no playable duration")
                results.append(PartResult(path, size, duration))
            except (OSError, ProbeError) as exc:
                bad.append(f"{path.name}: {exc}")
        if bad:
            raise SplitError("Some parts could not be verified and may be damaged:\n" + "\n".join(bad[:10]),
                             failed_parts=len(bad))

        numbers = [int(pattern.match(p.path.name).group(1)) for p in results]  # type: ignore[union-attr]
        warnings: list[str] = []
        notes: list[str] = []
        if numbers != list(range(1, len(numbers) + 1)):
            warnings.append("Part numbering has gaps; please check the output folder.")
        total = sum(r.duration for r in results)
        if abs(total - job.info.duration) > max(10.0, job.info.duration * 0.03):
            warnings.append(f"Combined part length ({total:.0f}s) differs from the movie ({job.info.duration:.0f}s).")
        if len(results) != expected_parts:
            notes.append(f"{len(results)} parts were created instead of the estimated {expected_parts}: "
                         "in Fast mode cuts snap to keyframes. Use Accurate mode for exact lengths.")
        elapsed = time.monotonic() - self._t0
        self._log(f"Verified {len(results)} parts in {elapsed:.1f}s")
        return SplitResult(job=job, parts=results, elapsed=elapsed, warnings=warnings, notes=notes)
