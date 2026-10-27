"""End-to-end test with real FFmpeg. Skipped automatically when FFmpeg is not installed."""
import subprocess

import pytest

from core.ffmpeg_locator import find_tools
from core.models import SplitCancelled, SplitError, SplitJob, ToolsMissingError
from core.naming import find_existing_parts
from core.probe import probe_video
from core.splitter import SplitEngine
from utils.proc import run_hidden

try:
    TOOLS = find_tools()
except ToolsMissingError:
    TOOLS = None

pytestmark = pytest.mark.skipif(TOOLS is None, reason="FFmpeg/FFprobe not installed")


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    path = tmp_path_factory.mktemp("src") / "Test Movie (1).mkv"
    cmd = [TOOLS.ffmpeg, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=65",
           "-f", "lavfi", "-i", "sine=frequency=440:duration=65", "-c:v", "libx264", "-g", "25",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)]
    run_hidden(cmd, check=True)
    return path


def make_job(sample, out_root, accurate=False, seg=20, overwrite=False):
    info = probe_video(TOOLS, sample)
    return SplitJob(info=info, out_dir=out_root / "Test Movie (1)", stem="Test Movie (1)", out_ext=".mkv",
                    segment_seconds=seg, accurate=accurate, overwrite=overwrite, expected_parts=4)


def test_fast_split_creates_verified_parts(sample, tmp_path):
    events = []
    result = SplitEngine(TOOLS, make_job(sample, tmp_path), on_progress=events.append).run()
    names = [p.path.name for p in result.parts]
    assert names == [f"Test Movie (1)_Part_{i:03d}.mkv" for i in range(1, 5)]
    assert abs(sum(p.duration for p in result.parts) - 65) < 3
    assert events and events[-1].percent == 100


def test_accurate_split_has_exact_lengths(sample, tmp_path):
    result = SplitEngine(TOOLS, make_job(sample, tmp_path, accurate=True)).run()
    durations = [round(p.duration) for p in result.parts]
    assert durations == [20, 20, 20, 5]


def test_existing_files_not_overwritten_without_confirmation(sample, tmp_path):
    SplitEngine(TOOLS, make_job(sample, tmp_path)).run()
    with pytest.raises(SplitError):
        SplitEngine(TOOLS, make_job(sample, tmp_path)).run()
    result = SplitEngine(TOOLS, make_job(sample, tmp_path, overwrite=True)).run()
    assert len(result.parts) == 4


def test_cancel_removes_partial_output(sample, tmp_path):
    job = make_job(sample, tmp_path, accurate=True, seg=5)
    engine = SplitEngine(TOOLS, job)
    engine.cancel()                      # cancelled before/while starting
    with pytest.raises(SplitCancelled):
        engine.run()
    assert find_existing_parts(job.out_dir, job.stem, job.out_ext) == []
