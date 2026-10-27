"""Turns raw FFmpeg output into messages a beginner can act on."""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, str]] = [
    (r"No space left on device|There is not enough space", "The destination drive ran out of free space. Free up space or choose another output location."),
    (r"Permission denied|Access is denied", "Windows denied access to the output location. Choose a folder you can write to, and check that antivirus or another program is not locking it."),
    (r"Invalid data found when processing input|moov atom not found|Invalid argument.*input", "The video file looks damaged or incomplete, so FFmpeg could not read it."),
    (r"not currently supported in container|Could not find tag for codec|incompatible with|Tag .* not supported", "One of the video/audio formats cannot be stored in this container with stream copy. Try Accurate mode, or use an MKV file."),
    (r"Unknown encoder|Encoder .* not found", "Your FFmpeg build does not include the encoder needed for Accurate mode. Install a full FFmpeg build (for example: winget install Gyan.FFmpeg)."),
    (r"Could not write header|Output file is empty", "FFmpeg could not start writing the output files."),
    (r"No such file or directory|cannot find the (?:file|path)", "A file or folder could not be found. It may have been moved or deleted while splitting."),
    (r"Error opening input|Error opening filters", "FFmpeg could not open the source video."),
]


def _last_error_line(lines: list[str]) -> str:
    for line in reversed(lines):
        if re.search(r"error|invalid|failed|denied|unable|cannot|could not", line, re.IGNORECASE):
            return line.strip()
    return lines[-1].strip() if lines else ""


def explain_ffmpeg_error(tail_lines: list[str], return_code: int) -> str:
    """Return a readable explanation plus the last relevant FFmpeg line."""
    blob = "\n".join(tail_lines)
    detail = _last_error_line(tail_lines)
    for pattern, message in _PATTERNS:
        if re.search(pattern, blob, re.IGNORECASE):
            return f"{message}\n\nFFmpeg said: {detail}" if detail else message
    base = f"FFmpeg stopped unexpectedly (exit code {return_code})."
    return f"{base}\n\nFFmpeg said: {detail}" if detail else base
