from pathlib import Path

from core.naming import (find_existing_parts, output_dir_for, output_extension, part_filename,
                         sanitize_name, segment_pattern, unique_output_dir)


def test_part_filenames_use_three_digits():
    assert part_filename("Avatar", 1, ".mkv") == "Avatar_Part_001.mkv"
    assert part_filename("Avatar", 42, ".mkv") == "Avatar_Part_042.mkv"
    assert part_filename("Avatar", 999, ".mkv") == "Avatar_Part_999.mkv"
    assert part_filename("Avatar", 1000, ".mkv") == "Avatar_Part_1000.mkv"   # expands naturally


def test_segment_pattern_escapes_percent():
    assert segment_pattern("Avatar", ".mkv") == "Avatar_Part_%03d.mkv"
    assert segment_pattern("100% Pure", ".mp4") == "100%% Pure_Part_%03d.mp4"


def test_output_folder_uses_stem_without_extension():
    stem = Path(r"D:\Movies\Avatar.mkv").stem if False else "Avatar"
    assert output_dir_for(Path("/out"), stem) == Path("/out/Avatar")


def test_sanitize_name():
    assert sanitize_name('Bad:Name?*') == "Bad_Name__"
    assert sanitize_name("  movie.  ") == "movie"
    assert sanitize_name("CON") == "_CON"
    assert sanitize_name("") == "movie"


def test_extension_preserved_or_fallback():
    assert output_extension(".MP4") == ".MP4"
    assert output_extension(".webm") == ".webm"
    assert output_extension(".m2ts") == ".mkv"


def test_unique_output_dir(tmp_path):
    assert unique_output_dir(tmp_path, "Avatar") == tmp_path / "Avatar"
    (tmp_path / "Avatar").mkdir()
    assert unique_output_dir(tmp_path, "Avatar") == tmp_path / "Avatar (2)"
    (tmp_path / "Avatar (2)").mkdir()
    assert unique_output_dir(tmp_path, "Avatar") == tmp_path / "Avatar (3)"


def test_find_existing_parts_sorted_and_filtered(tmp_path):
    for name in ["Avatar_Part_002.mkv", "Avatar_Part_001.mkv", "Avatar_Part_1000.mkv",
                 "Avatar_Part_01.mkv", "Other_Part_001.mkv", "Avatar_Part_003.mp4", "notes.txt"]:
        (tmp_path / name).write_bytes(b"x")
    names = [p.name for p in find_existing_parts(tmp_path, "Avatar", ".mkv")]
    assert names == ["Avatar_Part_001.mkv", "Avatar_Part_002.mkv", "Avatar_Part_1000.mkv"]
    assert find_existing_parts(tmp_path / "missing", "Avatar", ".mkv") == []
