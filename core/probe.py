"""FFprobe-based metadata reading and thumbnail extraction."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from core.models import FFmpegTools, ProbeError, StreamInfo, VideoInfo
from utils.proc import run_hidden


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_fps(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    if "/" in value:
        num, _, den = value.partition("/")
        d = _to_float(den)
        return _to_float(num) / d if d else 0.0
    return _to_float(value)


def _parse_tag_duration(text: str) -> float:
    m = re.match(r"^(\d+):(\d+):(\d+(?:\.\d+)?)", text or "")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def parse_probe_json(path: Path, data: dict) -> VideoInfo:
    """Convert ffprobe JSON into :class:`VideoInfo` (separated out for testing)."""
    fmt = data.get("format") or {}
    raw_streams = data.get("streams") or []
    streams: list[StreamInfo] = []
    for s in raw_streams:
        tags = {k.lower(): v for k, v in (s.get("tags") or {}).items()}
        streams.append(StreamInfo(
            index=_to_int(s.get("index")),
            codec_type=s.get("codec_type", ""),
            codec_name=s.get("codec_name", "unknown"),
            language=tags.get("language", ""),
            title=tags.get("title", ""),
            attached_pic=bool((s.get("disposition") or {}).get("attached_pic")),
            channels=_to_int(s.get("channels")),
        ))
    video = next((s for s in raw_streams
                  if s.get("codec_type") == "video" and not (s.get("disposition") or {}).get("attached_pic")), None)
    if video is None:
        raise ProbeError("No video stream was found in this file.")

    duration = _to_float(fmt.get("duration"))
    if duration <= 0:
        duration = _to_float(video.get("duration"))
    if duration <= 0:
        duration = _parse_tag_duration((video.get("tags") or {}).get("DURATION", ""))
    if duration <= 0:
        raise ProbeError("Could not determine the duration of this video.")

    try:
        size = int(_to_int(fmt.get("size")) or path.stat().st_size)
    except OSError:
        size = _to_int(fmt.get("size"))
    return VideoInfo(
        path=path, size_bytes=size,
        format_name=fmt.get("format_name", ""), format_long=fmt.get("format_long_name", ""),
        duration=duration, bit_rate=_to_int(fmt.get("bit_rate")),
        width=_to_int(video.get("width")), height=_to_int(video.get("height")),
        fps=_parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        video_codec=video.get("codec_name", "unknown"), streams=streams,
    )


def _run_ffprobe(tools: FFmpegTools, path: Path) -> dict:
    cmd = [tools.ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    try:
        proc = run_hidden(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    except OSError as exc:
        raise ProbeError(f"Could not run FFprobe: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - includes subprocess.TimeoutExpired
        raise ProbeError(f"FFprobe did not respond: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip().splitlines()
        raise ProbeError("This file could not be read as a video." + (f"\n{detail[-1]}" if detail else ""))
    try:
        return json.loads(proc.stdout or "{}")
    except ValueError as exc:
        raise ProbeError("FFprobe returned unreadable output.") from exc


def probe_video(tools: FFmpegTools, path: Path | str) -> VideoInfo:
    path = Path(path)
    if not path.is_file():
        raise ProbeError("The selected file does not exist.")
    if not os.access(path, os.R_OK):
        raise ProbeError("You do not have permission to read this file.")
    return parse_probe_json(path, _run_ffprobe(tools, path))


def probe_duration(tools: FFmpegTools, path: Path) -> float:
    """Duration in seconds of a (part) file; raises :class:`ProbeError` if unreadable."""
    cmd = [tools.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)]
    try:
        proc = run_hidden(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except Exception as exc:  # noqa: BLE001
        raise ProbeError(str(exc)) from exc
    if proc.returncode != 0:
        raise ProbeError((proc.stderr or "unreadable file").strip().splitlines()[-1])
    return _to_float((proc.stdout or "").strip())


def extract_thumbnail(tools: FFmpegTools, info: VideoInfo, width: int = 640) -> bytes | None:
    """Return JPEG bytes of a frame near the start of the video, or None."""
    for seek in (min(info.duration * 0.1, 300.0), 0.0):
        cmd = [tools.ffmpeg, "-v", "error", "-ss", f"{seek:.2f}", "-i", str(info.path), "-frames:v", "1",
               "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "4", "-"]
        try:
            proc = run_hidden(cmd, capture_output=True, timeout=45)
        except Exception:  # noqa: BLE001
            continue
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    return None
