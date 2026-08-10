"""Gear loading / Maple Warrior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hp_wash_thief.core.gear import (
    clip_segments_before_reset,
    effective_gear_for_level,
    gear_for_level,
    load_int_gear,
    maple_warrior_int,
    parse_int_gear,
    total_int,
)


def test_example_gear_file():
    segments = load_int_gear(Path("examples/int_gear.json"))
    assert gear_for_level(segments, 10) == 24
    assert gear_for_level(segments, 50) == 134
    assert gear_for_level(segments, 120) == 159
    # MW is % of base INT from level 10, not a gear JSON field.
    assert total_int(200, segments, 120, mw_percent=0.10, mw_from_level=10) == (
        200 + 159 + 20
    )


def test_maple_warrior_percent_of_base_int_only():
    assert maple_warrior_int(200, 9, mw_percent=0.10, mw_from_level=10) == 0
    assert maple_warrior_int(200, 10, mw_percent=0.10, mw_from_level=10) == 20
    assert maple_warrior_int(355, 50, mw_percent=0.10, mw_from_level=10) == 35
    segs = parse_int_gear([{"from_level": 1, "to_level": 200, "int_gear": 100}])
    # Gear is added flat; MW does not multiply gear.
    assert total_int(300, segs, 50) == 300 + 100 + 30


def test_overlap_rejected():
    with pytest.raises(ValueError, match="overlapping"):
        parse_int_gear(
            [
                {"from_level": 1, "to_level": 50, "int_gear": 10},
                {"from_level": 50, "to_level": 100, "int_gear": 20},
            ]
        )


def test_load_from_tmp(tmp_path: Path):
    path = tmp_path / "gear.json"
    path.write_text(
        json.dumps(
            [
                {"from_level": 1, "to_level": 200, "int_gear": 50},
            ]
        ),
        encoding="utf-8",
    )
    segs = load_int_gear(path)
    assert gear_for_level(segs, 150) == 50


def test_effective_gear_uses_fixed_int_after_reset():
    segments = load_int_gear(Path("examples/int_gear.json"))
    assert effective_gear_for_level(
        segments, 120, int_reset_level=155, int_gear_after_reset=50
    ) == 159
    assert effective_gear_for_level(
        segments, 155, int_reset_level=155, int_gear_after_reset=50
    ) == 50
    assert effective_gear_for_level(
        segments, 200, int_reset_level=155, int_gear_after_reset=50
    ) == 50


def test_total_int_after_reset_uses_post_reset_gear():
    segments = load_int_gear(Path("examples/int_gear.json"))
    before = total_int(
        4,
        segments,
        154,
        mw_percent=0.10,
        mw_from_level=10,
        int_reset_level=155,
        int_gear_after_reset=50,
    )
    after = total_int(
        4,
        segments,
        155,
        mw_percent=0.10,
        mw_from_level=10,
        int_reset_level=155,
        int_gear_after_reset=50,
    )
    assert before == 4 + 159 + 0
    assert after == 4 + 50 + 0


def test_clip_segments_before_reset():
    segments = load_int_gear(Path("examples/int_gear.json"))
    clipped = clip_segments_before_reset(segments, int_reset_level=155)
    assert clipped[-1].to_level == 154
    assert all(seg.to_level < 155 for seg in clipped)
