import pytest

from core.planner import estimate_part_count, plan_split, validate_segment


def test_example_from_spec():
    plan = plan_split(2 * 3600 + 10 * 60, 15 * 60)       # 02:10:00 split every 15 minutes
    assert plan.part_count == 9
    assert plan.last_part_duration == 10 * 60            # last part holds the remainder
    assert plan.parts[0].start == 0 and plan.parts[0].end == 900
    assert plan.parts[-1].end == 7800


def test_exact_multiple_has_no_empty_part():
    assert estimate_part_count(3600, 600) == 6
    assert plan_split(3600, 600).last_part_duration == 600


def test_segment_longer_than_movie_gives_single_part():
    plan = plan_split(300, 3600)
    assert plan.part_count == 1 and plan.parts[0].duration == 300


def test_tiny_remainder_still_counts():
    assert estimate_part_count(601, 600) == 2


def test_float_noise_does_not_add_part():
    assert estimate_part_count(0.3 * 10, 0.1 * 10) == 3


@pytest.mark.parametrize("seg", [0, -5, 0.5])
def test_invalid_segment(seg):
    assert validate_segment(100, seg) is not None
    with pytest.raises(ValueError):
        plan_split(100, seg)


def test_unknown_duration():
    assert validate_segment(0, 60) is not None


def test_parts_cover_whole_movie_without_gaps():
    plan = plan_split(1234.5, 100)
    assert plan.parts[0].start == 0
    for a, b in zip(plan.parts, plan.parts[1:]):
        assert a.end == b.start
    assert plan.parts[-1].end == 1234.5
