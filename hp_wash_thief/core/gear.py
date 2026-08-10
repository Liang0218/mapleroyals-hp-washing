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


def effective_gear_for_level(
    segments: Sequence[IntGearSegment],
    level: int,
    *,
    int_reset_level: int,
    int_gear_after_reset: int,
) -> int:
    """Gear INT before reset uses segments; from ``int_reset_level`` onward use fixed value."""
    if level >= int_reset_level:
        return int_gear_after_reset
    return gear_for_level(segments, level)


def clip_segments_before_reset(
    segments: Sequence[IntGearSegment], *, int_reset_level: int
) -> list[IntGearSegment]:
    """Keep only segment coverage strictly before INT reset."""
    clipped: list[IntGearSegment] = []
    cutoff = int_reset_level - 1
    for seg in segments:
        if seg.from_level >= int_reset_level:
            continue
        to_level = min(seg.to_level, cutoff)
        if seg.from_level <= to_level:
            clipped.append(
                IntGearSegment(
                    from_level=seg.from_level,
                    to_level=to_level,
                    int_gear=seg.int_gear,
                )
            )
    if not clipped:
        raise ValueError("no INT gear segments before int_reset_level")
    validate_int_gear(clipped)
    return clipped


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
    int_reset_level: int | None = None,
    int_gear_after_reset: int | None = None,
) -> int:
    """Total INT for level-up MP: base + gear + MW(% of base)."""
    if int_reset_level is not None and int_gear_after_reset is not None:
        gear = effective_gear_for_level(
            segments,
            level,
            int_reset_level=int_reset_level,
            int_gear_after_reset=int_gear_after_reset,
        )
    else:
        gear = gear_for_level(segments, level)
    mw = maple_warrior_int(
        base_int, level, mw_percent=mw_percent, mw_from_level=mw_from_level
    )
    return int(base_int) + int(gear) + int(mw)
