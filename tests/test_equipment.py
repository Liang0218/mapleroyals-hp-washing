"""Equipment → INT gear segment tests."""

from __future__ import annotations

from pathlib import Path

from hp_wash_thief.core.equipment import (
    EquipmentItem,
    compute_int_gear_segments,
    gear_int_at_level,
    load_equipment,
)
from hp_wash_thief.core.gear import clip_segments_before_reset


def test_default_equipment_template_all_zero_int():
    items = load_equipment(Path("examples/default_equipment.json"))
    assert len(items) == 29
    assert all(item.int_bonus == 0 for item in items)

    segments = clip_segments_before_reset(
        compute_int_gear_segments(items, max_level=154),
        int_reset_level=155,
    )
    assert len(segments) == 1
    assert segments[0].from_level == 1
    assert segments[0].to_level == 154
    assert segments[0].int_gear == 0
    assert gear_int_at_level(items, 10) == 0
    assert gear_int_at_level(items, 120) == 0


def test_current_int_gear_segments_clipped_by_reset_level():
    items = load_equipment(Path("examples/default_equipment.json"))
    # Inject one non-zero piece so breakpoints matter
    items = [
        *items,
        EquipmentItem(name="Test Wand", equip_type="Weapon", int_bonus=24, equip_level=10),
    ]
    panel_items = items

    segs155 = clip_segments_before_reset(
        compute_int_gear_segments(panel_items, max_level=154),
        int_reset_level=155,
    )
    segs120 = clip_segments_before_reset(
        compute_int_gear_segments(panel_items, max_level=119),
        int_reset_level=120,
    )
    assert segs155[-1].to_level == 154
    assert segs120[-1].to_level == 119
    assert gear_int_at_level(panel_items, 10) == 24
    assert segs155[-1].int_gear == 24
    assert segs120[-1].int_gear == 24


def test_ring_stacks_up_to_four():
    items = [
        EquipmentItem(name="R1", equip_type="Ring", int_bonus=5, equip_level=10),
        EquipmentItem(name="R2", equip_type="Ring", int_bonus=4, equip_level=10),
        EquipmentItem(name="R3", equip_type="Ring", int_bonus=3, equip_level=10),
        EquipmentItem(name="R4", equip_type="Ring", int_bonus=2, equip_level=10),
        EquipmentItem(name="R5", equip_type="Ring", int_bonus=10, equip_level=10),
    ]
    # Top four by INT: 10 + 5 + 4 + 3 (fifth ring excluded)
    assert gear_int_at_level(items, 10) == 22
