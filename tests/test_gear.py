"""Gear loading tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hp_wash_thief.core.gear import gear_for_level, load_int_gear, parse_int_gear, total_int


def test_example_gear_file(tmp_path: Path):
    src = Path("examples/int_gear.json")
    segments = load_int_gear(src)
    assert gear_for_level(segments, 10) == (15, 0)
    assert gear_for_level(segments, 50) == (80, 0)
    assert gear_for_level(segments, 100) == (120, 20)
    assert total_int(200, segments, 100) == 200 + 120 + 20


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
                {"from_level": 1, "to_level": 200, "int_gear": 50, "mw_int": 10},
            ]
        ),
        encoding="utf-8",
    )
    segs = load_int_gear(path)
    assert gear_for_level(segs, 150) == (50, 10)
