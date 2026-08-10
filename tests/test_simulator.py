"""Simulator / policy tests."""

from __future__ import annotations

from hp_wash_thief.core.formulas import EXTRA_MP_THRESHOLD_DEFAULT
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import Action, HP_ACTIONS, HpMode, MP_ACTIONS, PolicyName, SimulateConfig
from hp_wash_thief.core.policy import choose_early_action
from hp_wash_thief.core.simulator import simulate


GEAR = parse_int_gear(
    [
        {"from_level": 1, "to_level": 20, "int_gear": 15},
        {"from_level": 21, "to_level": 70, "int_gear": 80},
        {"from_level": 71, "to_level": 200, "int_gear": 120},
    ]
)


def test_policy_divergence():
    assert choose_early_action(PolicyName.MP_WASH_SHORTFALL, 60, 60) is Action.HP5
    assert choose_early_action(PolicyName.MP_WASH_SHORTFALL, 59, 60) is Action.MP5
    assert choose_early_action(PolicyName.INT_DUMP_SHORTFALL, 60, 60) is Action.HP5
    assert choose_early_action(PolicyName.INT_DUMP_SHORTFALL, 59, 60) is Action.INT5


def test_threshold_default_is_twelve_times_five():
    assert EXTRA_MP_THRESHOLD_DEFAULT == 60


def test_simulate_runs_and_resets_int():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=240,
            target_hp=20000,
            int_reset_level=140,
            int_gear=GEAR,
            mp_wash_end=135,
            extra_mp_threshold=60,
            hp_mode=HpMode.AVG,
        )
    )
    assert result.base_int_peak >= 240
    assert result.int_reached_level >= 30
    assert result.apr.int_reset_apr == result.base_int_peak - 4
    assert result.apr.total_apr == (
        result.apr.mp_wash_count
        + result.apr.method1_hp_wash_count
        + result.apr.method2_hp_wash_count
        + result.apr.int_reset_apr
    )
    assert any(row.action is Action.RESET_INT for row in result.plan)
    reset_idx = next(i for i, r in enumerate(result.plan) if r.action is Action.RESET_INT)
    assert all(r.base_int == 4 for r in result.plan[reset_idx:])
    assert result.final_display_hp > 0


def test_early_phase_lasts_until_target_int():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=300,
            target_hp=25000,
            int_reset_level=145,
            int_gear=GEAR,
            mp_wash_end=140,
            extra_mp_threshold=60,
        )
    )
    assert result.int_reached_level > 0
    # Before INT target, post-30 actions must be early-policy actions (HP/MP/INT/LUK).
    for row in result.plan:
        if 31 <= row.level < result.int_reached_level:
            assert row.action in HP_ACTIONS | MP_ACTIONS | {Action.INT5, Action.LUK5}


def test_int_dump_policy_has_zero_wash_apr_on_int5_rows():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_DUMP_SHORTFALL,
            target_base_int=300,
            target_hp=25000,
            int_reset_level=145,
            int_gear=GEAR,
            mp_wash_end=140,
            extra_mp_threshold=60,
        )
    )
    int5_rows = [
        r
        for r in result.plan
        if r.action is Action.INT5 and 31 <= r.level <= result.int_reached_level
    ]
    assert int5_rows, "expected some INT5 shortfall levels before target INT"
    assert all(r.apr_spent == 0 for r in int5_rows)


def test_job_advance_levels_grant_extra_ap():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=350,
            target_hp=25000,
            int_reset_level=145,
            int_gear=GEAR,
            mp_wash_end=140,
            extra_mp_threshold=60,
        )
    )

    def fresh_ap_total(row) -> int:
        return (
            row.fresh_ap_hp
            + row.fresh_ap_mp
            + row.fresh_ap_int
            + row.fresh_ap_luk
            + row.fresh_ap_dex
        )

    lv10 = next(r for r in result.plan if r.level == 10)
    lv70 = next(r for r in result.plan if r.level == 70)
    lv120 = next(r for r in result.plan if r.level == 120)
    assert fresh_ap_total(lv10) == 5
    assert fresh_ap_total(lv70) == 10
    assert fresh_ap_total(lv120) == 10


def test_hardcore_policy_can_hp_wash_before_30():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_HARDCORE,
            target_base_int=300,
            target_hp=25000,
            int_reset_level=145,
            int_gear=GEAR,
            mp_wash_end=140,
        )
    )
    pre30_hp = [
        r
        for r in result.plan
        if 10 <= r.level < 30
        and r.action is Action.HARDCORE_GREEDY
        and r.fresh_ap_hp > 0
    ]
    assert pre30_hp, "expected Method 1 HP washes between levels 10–29"
    assert any(r.fresh_ap_hp == 1 for r in pre30_hp), "expected some single-HP greedy levels"
    assert not any(
        r.fresh_ap_mp > 0 for r in result.plan if r.level < 30
    ), "Policy C must not MP wash before level 30"


def test_partial_hp1_leaves_remaining_ap_for_int():
    """Extra MP = 12 → only 1 Method1; other 4 fresh AP go to INT (0 APR)."""
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_HARDCORE,
            target_base_int=500,
            target_hp=25000,
            int_reset_level=145,
            int_gear=GEAR,
            mp_wash_end=140,
        )
    )
    partial = [
        r
        for r in result.plan
        if r.action is Action.HARDCORE_GREEDY and r.apr_spent == 1 and r.fresh_ap_int >= 1
    ]
    assert partial, "expected greedy rows with 1 HP wash and leftover AP dumped to INT"


def test_method2_can_close_gap():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=400,
            target_hp=30000,
            int_reset_level=145,
            int_gear=GEAR,
            mp_wash_end=145,
            extra_mp_threshold=60,
            auto_method2=True,
        )
    )
    assert result.final_display_hp > 15000
    assert result.apr.total_apr > 0
