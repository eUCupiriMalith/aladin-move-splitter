from utils.timefmt import format_hms, format_human, hms_to_seconds, human_size, split_hms


def test_format_hms():
    assert format_hms(0) == "00:00:00"
    assert format_hms(7800) == "02:10:00"
    assert format_hms(3599.6) == "01:00:00"
    assert format_hms(360000) == "100:00:00"
    assert format_hms(None) == "00:00:00"
    assert format_hms(-5) == "00:00:00"


def test_format_human():
    assert format_human(45) == "45s"
    assert format_human(125) == "2m 05s"
    assert format_human(7805) == "2h 10m 05s"


def test_hms_roundtrip():
    assert hms_to_seconds(1, 2, 3) == 3723
    assert split_hms(3723) == (1, 2, 3)


def test_human_size():
    assert human_size(0) == "0 B"
    assert human_size(512) == "512 B"
    assert human_size(1024 ** 3 * 4.5) == "4.50 GB"
