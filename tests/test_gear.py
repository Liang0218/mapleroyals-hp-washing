"""Gear loading / Maple Warrior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hp_wash_thief.core.gear import (
    gear_for_level,
    load_int_gear,
    maple_warrior_int,
    parse_int_gear,
    total_int,
)


def test_example_gear_file():
    segments = load_int_gear(Path("examples/int_gear.json"))
    assert gear_for_level(segments, 10) == (24, 0)
    assert gear_for_level(segments, 50) == (134, 0)
    assert gear_for_level(segments, 120) == (159, 0)
    # MW is % of base INT from level 10, not a flat gear field.
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
                {"from_level": 1, "to_level": 200, "int_gear": 50, "mw_int": 0},
            ]
        ),
        encoding="utf-8",
    )
    segs = load_int_gear(path)
    assert gear_for_level(segs, 150) == (50, 0)
