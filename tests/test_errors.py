from core.errors import explain_ffmpeg_error


def test_disk_full_message():
    msg = explain_ffmpeg_error(["av_interleaved_write_frame(): No space left on device"], 1)
    assert "free space" in msg


def test_permission_message():
    assert "denied access" in explain_ffmpeg_error(["Error: Permission denied"], 1)


def test_unknown_error_includes_exit_code_and_last_line():
    msg = explain_ffmpeg_error(["something odd", "Conversion failed!"], 7)
    assert "exit code 7" in msg and "Conversion failed!" in msg
