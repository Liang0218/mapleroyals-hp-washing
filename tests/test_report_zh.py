"""Report localization smoke tests."""

from __future__ import annotations

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import OptimizeConfig, PolicyName, SimulateConfig
from hp_wash_thief.core.report import format_optimize_report, format_simulate_report


GEAR = parse_int_gear([{"from_level": 1, "to_level": 200, "int_gear": 100}])


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
    assert "政策比較" in text
    assert "優勝方案" in text
    assert "總 APR" in text


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
    assert "模擬結果" in text
    assert any("創角 AP" in row.notes or "堆 INT" in row.notes or "建 DEX" in row.notes for row in result.plan)
