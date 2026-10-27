"""Plain data classes and exceptions shared across the application."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class MovieSplitterError(Exception):
    """Base class for all expected, user-presentable errors."""


class ToolsMissingError(MovieSplitterError):
    """FFmpeg or FFprobe could not be located."""


class ProbeError(MovieSplitterError):
    """A video file could not be read or analysed."""


class SplitCancelled(MovieSplitterError):
    """The user cancelled the split operation."""


class SplitError(MovieSplitterError):
    """The split failed. ``failed_parts`` is the number of parts known to be bad."""

    def __init__(self, message: str, failed_parts: int = 1) -> None:
        super().__init__(message)
        self.failed_parts = failed_parts


@dataclass(frozen=True)
class StreamInfo:
    index: int
    codec_type: str            # video / audio / subtitle / data / attachment
    codec_name: str
    language: str = ""
    title: str = ""
    attached_pic: bool = False  # cover-art "video" streams
    channels: int = 0


@dataclass
class VideoInfo:
    path: Path
    size_bytes: int
    format_name: str
    format_long: str
    duration: float
    bit_rate: int
    width: int
    height: int
    fps: float
    video_codec: str
    streams: list[StreamInfo] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def stem(self) -> str:
        return self.path.stem

    @property
    def ext(self) -> str:
        return self.path.suffix

    @property
    def resolution(self) -> str:
        return f"{self.width} × {self.height}" if self.width and self.height else "Unknown"

    @property
    def audio_streams(self) -> list[StreamInfo]:
        return [s for s in self.streams if s.codec_type == "audio"]

    @property
    def subtitle_streams(self) -> list[StreamInfo]:
        return [s for s in self.streams if s.codec_type == "subtitle"]


@dataclass(frozen=True)
class FFmpegTools:
    ffmpeg: str
    ffprobe: str
    version: str


@dataclass
class SplitJob:
    info: VideoInfo
    out_dir: Path              # final folder, e.g. D:\Split Movies\Avatar
    stem: str                  # sanitised base name used for part files
    out_ext: str               # extension of the part files, e.g. ".mkv"
    segment_seconds: float
    accurate: bool = False
    overwrite: bool = False    # user confirmed replacing existing parts
    expected_parts: int = 0


@dataclass(frozen=True)
class PartResult:
    path: Path
    size_bytes: int
    duration: float


@dataclass
class SplitResult:
    job: SplitJob
    parts: list[PartResult]
    elapsed: float
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
