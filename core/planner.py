"""Split planning: how many parts will a movie be divided into?"""
from __future__ import annotations

import math
from dataclasses import dataclass

MIN_SEGMENT_SECONDS = 1.0
_EPS = 1e-6


@dataclass(frozen=True)
class PartPlan:
    index: int      # 1-based
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class SplitPlan:
    total_duration: float
    segment_seconds: float
    parts: tuple[PartPlan, ...]

    @property
    def part_count(self) -> int:
        return len(self.parts)

    @property
    def last_part_duration(self) -> float:
        return self.parts[-1].duration if self.parts else 0.0


def validate_segment(total_duration: float, segment_seconds: float) -> str | None:
    """Return a human-readable error, or ``None`` when the values are usable."""
    if total_duration is None or total_duration <= 0:
        return "The duration of the selected video is unknown."
    if segment_seconds is None or segment_seconds <= 0:
        return "Split duration must be greater than zero."
    if segment_seconds < MIN_SEGMENT_SECONDS:
        return "Split duration must be at least 1 second."
    return None


def estimate_part_count(total_duration: float, segment_seconds: float) -> int:
    """Number of parts; the final part holds whatever remains."""
    error = validate_segment(total_duration, segment_seconds)
    if error:
        raise ValueError(error)
    return max(1, math.ceil(total_duration / segment_seconds - _EPS))


def plan_split(total_duration: float, segment_seconds: float) -> SplitPlan:
    count = estimate_part_count(total_duration, segment_seconds)
    parts = []
    for i in range(count):
        start = i * segment_seconds
        end = min(total_duration, start + segment_seconds)
        parts.append(PartPlan(index=i + 1, start=start, end=end))
    return SplitPlan(total_duration, segment_seconds, tuple(parts))
