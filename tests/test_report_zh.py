"""Report localization smoke tests."""

from __future__ import annotations

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import OptimizeConfig, PolicyName, SimulateConfig
from hp_wash_thief.core.report import (
    PLAN_CSV_HINT,
    format_optimize_report,
    format_simulate_report,
    format_ui_guide,
    action_description,
)


GEAR = parse_int_gear([{"from_level": 1, "to_level": 200, "int_gear": 100}])


def test_ui_guide_mentions_equipment_first():
    text = format_ui_guide()
    assert "裝備 Equipment" in text
    assert len(text.splitlines()) <= 12


def test_format_int_gear_preview():
    from hp_wash_thief.core.equipment import format_int_gear_preview, load_equipment
    from hp_wash_thief.core.gear import clip_segments_before_reset
    from hp_wash_thief.core.equipment import compute_int_gear_segments
    from pathlib import Path

    items = load_equipment(Path("examples/default_equipment.json"))
    segs = clip_segments_before_reset(
        compute_int_gear_segments(items, max_level=154), int_reset_level=155
    )
    text = format_int_gear_preview(segs, int_reset_level=155, int_gear_after_reset=50)
    assert "等級區間" in text
    assert "10 – 14" in text or "10 – 14" in text.replace("  ", " ")
    assert "24" in text
    assert "≥155" in text


def test_optimize_report_is_chinese():
    result = optimize(
        OptimizeConfig(
            target_hp=18000,
            int_reset_level=120,
            int_gear=GEAR,
            policies=[PolicyName.MP_WASH_SHORTFALL],
            target_base_int_min=200,
            target_base_int_max=240,
            target_base_int_step=40,
            mp_wash_end_min=80,
            top_n=2,
        )
    )
    text = format_optimize_report(result)
    assert "懶人包" in text
    assert "政策比較" in text
    assert "A vs B vs C" in text
    assert "優勝方案" in text
    assert "總 APR" in text
    assert PLAN_CSV_HINT in text
    assert "Lv   Action" not in text


def test_simulate_report_and_notes_chinese():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=200,
            target_hp=15000,
            int_reset_level=120,
            int_gear=GEAR,
            mp_wash_end=100,
        )
    )
    text = format_simulate_report(result)
    assert "懶人包" in text
    assert "模擬結果" in text
    assert PLAN_CSV_HINT in text
    assert "Lv   Action" not in text
    assert any("創角 AP" in row.notes or "堆 INT" in row.notes or "建 DEX" in row.notes for row in result.plan)


def test_hardcore_report_shows_per_wash_threshold_not_60():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_HARDCORE,
            target_base_int=200,
            target_hp=15000,
            int_reset_level=120,
            int_gear=GEAR,
            mp_wash_end=100,
        )
    )
    text = format_simulate_report(result)
    assert "門檻=12" in text
    assert "非 60" in text
    assert "Extra MP 門檻=60" not in text


def test_action_descriptions_cover_all_actions():
    from hp_wash_thief.core.models import Action

    for action in Action:
        if action is Action.NONE:
            continue
        desc = action_description(action)
        assert desc and desc != action.value
