from pathlib import Path

from core.command import build_split_command, select_streams
from core.models import FFmpegTools, SplitJob, StreamInfo, VideoInfo

TOOLS = FFmpegTools("ffmpeg", "ffprobe", "test")
STREAMS = [
    StreamInfo(0, "video", "h264"),
    StreamInfo(1, "audio", "aac"),
    StreamInfo(2, "subtitle", "subrip"),
    StreamInfo(3, "subtitle", "hdmv_pgs_subtitle"),
    StreamInfo(4, "video", "mjpeg", attached_pic=True),
]


def make_job(ext=".mkv", accurate=False, stem="My Movie"):
    info = VideoInfo(Path("/in/My Movie" + ext), 1000, "matroska", "", 7800.0, 0, 1920, 1080, 24.0, "h264", list(STREAMS))
    return SplitJob(info=info, out_dir=Path("/out/My Movie"), stem=stem, out_ext=ext, segment_seconds=900, accurate=accurate)


def test_fast_mode_uses_stream_copy_and_segment_muxer():
    cmd, dropped = build_split_command(TOOLS, make_job())
    assert cmd[cmd.index("-c") + 1] == "copy"
    assert "segment" in cmd and "-force_key_frames" not in cmd
    assert cmd[-1].replace("\\", "/") == "/out/My Movie/My Movie_Part_%03d.mkv"
    assert "-segment_start_number" in cmd and cmd[cmd.index("-segment_start_number") + 1] == "1"
    assert any("cover art" in d for d in dropped)


def test_paths_with_spaces_stay_single_arguments():
    cmd, _ = build_split_command(TOOLS, make_job())
    assert str(Path("/in/My Movie.mkv")) in cmd


def test_accurate_mode_reencodes_with_forced_keyframes():
    cmd, _ = build_split_command(TOOLS, make_job(accurate=True))
    assert "libx264" in cmd and "-force_key_frames" in cmd
    assert cmd[cmd.index("-force_key_frames") + 1] == "expr:gte(t,n_forced*900.000)"
    assert "copy" in cmd  # mkv audio is still copied


def test_mkv_keeps_all_subtitles_and_drops_cover_art():
    keep, dropped, has_subs = select_streams(STREAMS, ".mkv")
    assert keep == [0, 1, 2, 3] and has_subs and len(dropped) == 1


def test_mp4_keeps_only_text_subtitles_as_mov_text():
    keep, dropped, has_subs = select_streams(STREAMS, ".mp4")
    assert keep == [0, 1, 2] and has_subs
    cmd, _ = build_split_command(TOOLS, make_job(".mp4"))
    assert cmd[cmd.index("-c:s") + 1] == "mov_text"
    assert "movflags=+faststart" in cmd


def test_avi_drops_subtitles():
    keep, _, has_subs = select_streams(STREAMS, ".avi")
    assert keep == [0, 1] and not has_subs


def test_webm_accurate_uses_vp9_opus():
    cmd, _ = build_split_command(TOOLS, make_job(".webm", accurate=True))
    assert "libvpx-vp9" in cmd and "libopus" in cmd
