"""Equipment → INT gear segment tests."""

from __future__ import annotations

from pathlib import Path

from hp_wash_thief.core.equipment import (
    compute_int_gear_segments,
    gear_int_at_level,
    load_equipment,
)
from hp_wash_thief.core.gear import clip_segments_before_reset, gear_for_level, load_int_gear


def test_default_equipment_matches_int_gear_example():
    items = load_equipment(Path("examples/default_equipment.json"))
    segments = compute_int_gear_segments(items, max_level=154)
    segments = clip_segments_before_reset(segments, int_reset_level=155)
    expected = load_int_gear(Path("examples/int_gear.json"))

    assert [(s.from_level, s.to_level, s.int_gear) for s in segments] == [
        (s.from_level, s.to_level, s.int_gear) for s in expected
    ]
    assert gear_int_at_level(items, 10) == 24
    assert gear_int_at_level(items, 50) == 134
    assert gear_int_at_level(items, 120) == 159
    assert gear_for_level(segments, 120) == 159


def test_ring_stacks_up_to_four():
    items = load_equipment(Path("examples/default_equipment.json"))
    assert gear_int_at_level(items, 10) == 24  # four 0-int rings
    assert gear_int_at_level(items, 70) == 138  # almighty + Circle Of Ancient Thought + two 0 rings
