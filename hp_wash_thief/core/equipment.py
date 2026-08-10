"""Equipment list → level-based INT gear segments.

Each equipment type (except Ring) contributes at most one worn piece: the
available item with the highest INT for that type. Ring allows up to four
simultaneous pieces (sum of top four by INT).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence, Union

from hp_wash_thief.core.gear import validate_int_gear
from hp_wash_thief.core.models import IntGearSegment

EQUIPMENT_TYPES: tuple[str, ...] = (
    "Hat",
    "Face Accessory",
    "Eye Accessory",
    "Earring",
    "Pendant",
    "Medal",
    "Shoulder",
    "Overall",
    "Cape",
    "Belt",
    "Glove",
    "Weapon",
    "Shield",
    "Ring",
    "Shoe",
)

RING_TYPE = "Ring"
RING_SLOTS = 4
SINGLE_SLOT_TYPES = tuple(t for t in EQUIPMENT_TYPES if t != RING_TYPE)


@dataclass(frozen=True)
class EquipmentItem:
    name: str
    equip_type: str
    int_bonus: int
    equip_level: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.equip_type,
            "int": self.int_bonus,
            "equip_level": self.equip_level,
        }


def parse_equipment(raw: Sequence[dict]) -> list[EquipmentItem]:
    items: list[EquipmentItem] = []
    for row in raw:
        equip_type = str(row["type"])
        if equip_type not in EQUIPMENT_TYPES:
            raise ValueError(f"unknown equipment type: {equip_type}")
        int_bonus = int(row["int"])
        equip_level = int(row["equip_level"])
        if int_bonus < 0:
            raise ValueError(f"int must be >= 0 for {row.get('name', equip_type)}")
        if equip_level < 1:
            raise ValueError(f"equip_level must be >= 1 for {row.get('name', equip_type)}")
        items.append(
            EquipmentItem(
                name=str(row.get("name", "")),
                equip_type=equip_type,
                int_bonus=int_bonus,
                equip_level=equip_level,
            )
        )
    return items


def load_equipment(path: Union[str, Path]) -> list[EquipmentItem]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("equipment JSON must be a list")
    return parse_equipment(raw)


def equipment_to_dicts(items: Iterable[EquipmentItem]) -> list[dict]:
    return [item.to_dict() for item in items]


def _available(items: Sequence[EquipmentItem], level: int) -> list[EquipmentItem]:
    return [item for item in items if item.equip_level <= level]


def _best_single(items: Sequence[EquipmentItem]) -> int:
    if not items:
        return 0
    best = max(items, key=lambda item: (item.int_bonus, item.equip_level))
    return best.int_bonus


def _ring_total(items: Sequence[EquipmentItem]) -> int:
    rings = sorted(items, key=lambda item: (-item.int_bonus, -item.equip_level))
    return sum(item.int_bonus for item in rings[:RING_SLOTS])


def gear_int_at_level(items: Sequence[EquipmentItem], level: int) -> int:
    """Total worn equipment INT at ``level``."""
    available = _available(items, level)
    by_type: dict[str, list[EquipmentItem]] = {}
    for item in available:
        by_type.setdefault(item.equip_type, []).append(item)

    total = 0
    for equip_type in SINGLE_SLOT_TYPES:
        total += _best_single(by_type.get(equip_type, []))
    total += _ring_total(by_type.get(RING_TYPE, []))
    return total


def compute_int_gear_segments(
    items: Sequence[EquipmentItem], *, max_level: int = 200
) -> list[IntGearSegment]:
    """Merge consecutive levels with the same total equipment INT."""
    if max_level < 1:
        raise ValueError("max_level must be >= 1")
    if not items:
        return [IntGearSegment(from_level=1, to_level=max_level, int_gear=0)]

    breakpoints = sorted({1, max_level, *(item.equip_level for item in items)})
    segments: list[IntGearSegment] = []
    for idx, start in enumerate(breakpoints):
        if start > max_level:
            break
        end = breakpoints[idx + 1] - 1 if idx + 1 < len(breakpoints) else max_level
        end = min(end, max_level)
        int_gear = gear_int_at_level(items, start)
        if segments and segments[-1].int_gear == int_gear:
            segments[-1] = IntGearSegment(segments[-1].from_level, end, int_gear)
        else:
            segments.append(IntGearSegment(from_level=start, to_level=end, int_gear=int_gear))

    validate_int_gear(segments)
    return segments


def segments_to_json(segments: Sequence[IntGearSegment], *, indent: int = 2) -> str:
    payload = [
        {
            "from_level": seg.from_level,
            "to_level": seg.to_level,
            "int_gear": seg.int_gear,
        }
        for seg in segments
    ]
    return json.dumps(payload, ensure_ascii=False, indent=indent) + "\n"


def format_int_gear_preview(
    segments: Sequence[IntGearSegment],
    *,
    int_reset_level: int,
    int_gear_after_reset: int,
) -> str:
    """Human-readable level → equipment INT table for the UI."""
    lines = [
        "等級區間      智裝 INT",
        "──────────────────────",
    ]
    for seg in segments:
        lines.append(
            f"  {seg.from_level:>3} – {seg.to_level:<3}      {seg.int_gear:>3}"
        )
    lines.append("")
    lines.append(f"INT reset 後（≥{int_reset_level}）  智裝 INT = {int_gear_after_reset}")
    return "\n".join(lines)
