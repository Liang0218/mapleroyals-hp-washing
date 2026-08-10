"""Simulator / policy tests."""

from __future__ import annotations

from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import Action, HpMode, PolicyName, SimulateConfig
from hp_wash_thief.core.policy import choose_early_action
from hp_wash_thief.core.simulator import simulate


GEAR = parse_int_gear(
    [
        {"from_level": 1, "to_level": 20, "int_gear": 15, "mw_int": 0},
        {"from_level": 21, "to_level": 70, "int_gear": 80, "mw_int": 0},
        {"from_level": 71, "to_level": 200, "int_gear": 120, "mw_int": 20},
    ]
)


def test_policy_divergence():
    assert choose_early_action(PolicyName.MP_WASH_SHORTFALL, 60, 60) is Action.HP5
    assert choose_early_action(PolicyName.MP_WASH_SHORTFALL, 59, 60) is Action.MP5
    assert choose_early_action(PolicyName.INT_DUMP_SHORTFALL, 60, 60) is Action.HP5
    assert choose_early_action(PolicyName.INT_DUMP_SHORTFALL, 59, 60) is Action.INT5


def test_simulate_runs_and_resets_int():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=240,
            target_hp=20000,
            int_reset_level=140,
            int_gear=GEAR,
            early_phase_end=70,
            mp_wash_end=135,
            extra_mp_threshold=60,
            hp_mode=HpMode.AVG,
        )
    )
    assert result.base_int_peak >= 240
    assert result.apr.int_reset_apr == result.base_int_peak - 4
    assert result.apr.total_apr == (
        result.apr.mp_wash_count
        + result.apr.method1_hp_wash_count
        + result.apr.method2_hp_wash_count
        + result.apr.int_reset_apr
    )
    assert any(row.action is Action.RESET_INT for row in result.plan)
    # After reset, late washes must not rebuild INT.
    reset_idx = next(i for i, r in enumerate(result.plan) if r.action is Action.RESET_INT)
    assert all(r.base_int == 4 for r in result.plan[reset_idx:])
    assert result.final_display_hp > 0


def test_int_dump_policy_has_zero_wash_apr_on_int5_rows():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_DUMP_SHORTFALL,
            target_base_int=300,
            target_hp=25000,
            int_reset_level=145,
            int_gear=GEAR,
            early_phase_end=70,
            mp_wash_end=140,
            extra_mp_threshold=60,
        )
    )
    int5_rows = [r for r in result.plan if r.action is Action.INT5 and 31 <= r.level <= 70]
    assert int5_rows, "expected some INT5 shortfall levels in early phase"
    assert all(r.apr_spent == 0 for r in int5_rows)


def test_method2_can_close_gap():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=400,
            target_hp=30000,
            int_reset_level=145,
            int_gear=GEAR,
            early_phase_end=70,
            mp_wash_end=145,
            extra_mp_threshold=60,
            auto_method2=True,
        )
    )
    # High INT + long MP wash should get close; Method2 may or may not be needed.
    assert result.final_display_hp > 15000
    assert result.apr.total_apr > 0
