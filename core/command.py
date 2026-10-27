"""Builds the FFmpeg command line for splitting a video.

We use FFmpeg's *segment muxer* so the whole movie is processed in ONE pass:
no gaps or overlaps between parts, and a single progress stream to read.

Fast mode (default): ``-c copy``. No quality loss and very fast, but cuts can only
happen on keyframes, so each part may be a few seconds longer than requested.

Accurate mode: re-encodes video and forces a keyframe exactly at every split point,
so parts have precisely the requested length (slower; quality depends on the CRF used).
"""
from __future__ import annotations

from core.models import FFmpegTools, SplitJob, StreamInfo
from core.naming import SEGMENT_FORMATS, segment_pattern

TEXT_SUBTITLE_CODECS = {"subrip", "srt", "ass", "ssa", "webvtt", "mov_text", "text"}
_MP4_FAMILY = {".mp4", ".m4v", ".mov"}


def container_family(ext: str) -> str:
    ext = ext.lower()
    if ext == ".mkv":
        return "mkv"
    if ext in _MP4_FAMILY:
        return "mp4"
    if ext == ".webm":
        return "webm"
    return "other"


def select_streams(streams: list[StreamInfo], ext: str) -> tuple[list[int], list[str], bool]:
    """Pick the streams to keep. Returns (indexes, dropped descriptions, has_subtitles)."""
    family = container_family(ext)
    keep: list[int] = []
    dropped: list[str] = []
    has_subs = False
    for s in streams:
        if s.codec_type == "video":
            if s.attached_pic:
                dropped.append(f"cover art (stream #{s.index})")
            else:
                keep.append(s.index)
        elif s.codec_type == "audio":
            keep.append(s.index)
        elif s.codec_type == "subtitle":
            ok = family == "mkv" or (family in ("mp4", "webm") and s.codec_name in TEXT_SUBTITLE_CODECS)
            if ok:
                keep.append(s.index)
                has_subs = True
            else:
                dropped.append(f"subtitle stream #{s.index} ({s.codec_name}) - not supported by {ext} output")
        else:
            dropped.append(f"{s.codec_type} stream #{s.index} ({s.codec_name})")
    return keep, dropped, has_subs


def _codec_args(job: SplitJob, family: str, has_subs: bool) -> list[str]:
    args: list[str] = []
    if not job.accurate:
        args += ["-c", "copy"]
    else:
        if family == "webm":
            args += ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-deadline", "good", "-cpu-used", "5", "-row-mt", "1"]
            args += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
            if family == "mkv":
                args += ["-c:a", "copy"]
            elif job.out_ext.lower() == ".avi":
                args += ["-c:a", "libmp3lame", "-b:a", "192k"]
            else:
                args += ["-c:a", "aac", "-b:a", "192k"]
        args += ["-max_muxing_queue_size", "4096"]
    if has_subs:
        if family == "mp4":
            args += ["-c:s", "mov_text"]
        elif family == "webm":
            args += ["-c:s", "webvtt"]
        else:
            args += ["-c:s", "copy"]
    return args


def build_split_command(tools: FFmpegTools, job: SplitJob) -> tuple[list[str], list[str]]:
    """Return ``(argv, dropped_stream_descriptions)``. argv is a list: no shell quoting issues."""
    ext = job.out_ext
    family = container_family(ext)
    keep, dropped, has_subs = select_streams(job.info.streams, ext)

    cmd = [tools.ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "info",
           "-progress", "pipe:1", "-nostats", "-i", str(job.info.path)]
    for index in keep:
        cmd += ["-map", f"0:{index}"]
    cmd += ["-map_chapters", "-1"]       # whole-movie chapters would be wrong inside each part
    cmd += _codec_args(job, family, has_subs)

    seg = f"{job.segment_seconds:.3f}"
    if job.accurate:
        cmd += ["-force_key_frames", f"expr:gte(t,n_forced*{seg})", "-segment_time_delta", "0.05"]
    cmd += ["-f", "segment", "-segment_time", seg, "-segment_start_number", "1", "-reset_timestamps", "1"]
    fmt = SEGMENT_FORMATS.get(ext.lower())
    if fmt:
        cmd += ["-segment_format", fmt]
    if family == "mp4":
        cmd += ["-segment_format_options", "movflags=+faststart"]
    cmd.append(str(job.out_dir / segment_pattern(job.stem, ext)))
    return cmd, dropped
