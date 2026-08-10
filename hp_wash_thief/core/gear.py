"""INT gear / Maple Warrior lookup by level."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Sequence, Union

from hp_wash_thief.core.models import IntGearSegment


def load_int_gear(path: Union[str, Path]) -> list[IntGearSegment]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("INT gear JSON must be a list of segments")
    return parse_int_gear(raw)


def parse_int_gear(raw: Sequence[dict]) -> list[IntGearSegment]:
    segments: list[IntGearSegment] = []
    for item in raw:
        segments.append(
            IntGearSegment(
                from_level=int(item["from_level"]),
                to_level=int(item["to_level"]),
                int_gear=int(item.get("int_gear", 0)),
            )
        )
    validate_int_gear(segments)
    return segments


def validate_int_gear(segments: Iterable[IntGearSegment]) -> None:
    ordered = sorted(segments, key=lambda s: (s.from_level, s.to_level))
    if not ordered:
        raise ValueError("INT gear must contain at least one segment")
    for seg in ordered:
        if seg.from_level > seg.to_level:
            raise ValueError(
                f"invalid segment {seg.from_level}-{seg.to_level}: from_level > to_level"
            )
        if seg.int_gear < 0:
            raise ValueError("int_gear must be >= 0")
    for prev, cur in zip(ordered, ordered[1:]):
        if cur.from_level <= prev.to_level:
            raise ValueError(
                f"overlapping INT gear segments: {prev.from_level}-{prev.to_level} and "
                f"{cur.from_level}-{cur.to_level}"
            )


def gear_for_level(segments: Sequence[IntGearSegment], level: int) -> int:
    """Return int_gear for a level. Missing coverage → 0."""
    for seg in segments:
        if seg.covers(level):
            return seg.int_gear
    return 0


def maple_warrior_int(
    base_int: int, level: int, *, mw_percent: float = 0.10, mw_from_level: int = 10
) -> int:
    """Maple Warrior INT bonus = floor(base_int * mw_percent) from mw_from_level onward.

    Uses base INT only (equipment INT is not multiplied). Default is 10% from level 10.
    """
    if level < mw_from_level or mw_percent <= 0:
        return 0
    return int(max(0, int(base_int)) * float(mw_percent))


def total_int(
    base_int: int,
    segments: Sequence[IntGearSegment],
    level: int,
    *,
    mw_percent: float = 0.10,
    mw_from_level: int = 10,
) -> int:
    """Total INT for level-up MP: base + gear + MW(% of base)."""
    gear = gear_for_level(segments, level)
    mw = maple_warrior_int(
        base_int, level, mw_percent=mw_percent, mw_from_level=mw_from_level
    )
    return int(base_int) + int(gear) + int(mw)
