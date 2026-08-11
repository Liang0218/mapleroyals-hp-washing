"""Regression locks for wash behavior and APR accounting.

These tests pin known relationships and golden numbers so refactors that change
formula / phase logic fail loudly. Update golden values intentionally when the
model changes on purpose.
"""

from __future__ import annotations

import pytest

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.models import (
    Action,
    HpMode,
    OptimizeConfig,
    PolicyName,
    SimulateConfig,
)
from hp_wash_thief.core.report import format_optimize_report, policy_label, policy_short
from tests.helpers import assert_apr_identity, assert_plan_invariants


def _sim(
    example_gear,
    *,
    policy: PolicyName,
    mp5_start_level: int = 50,
    target_base_int: int = 320,
    target_hp: int = 27000,
    mp_wash_end: int = 120,
):
    return simulate(
        SimulateConfig(
            policy=policy,
            target_base_int=target_base_int,
            target_hp=target_hp,
            int_reset_level=155,
            int_gear=example_gear,
            mp_wash_end=mp_wash_end,
            mp5_start_level=mp5_start_level,
            hp_mode=HpMode.AVG,
            extra_mp_threshold=60,
            int_gear_after_reset=50,
        )
    )


@pytest.mark.regression
def test_regression_policy_e_mp5_start_31_matches_policy_a(example_gear):
    """mp5_start_level=31 → shortfall always MP5 → identical to Policy A."""
    a = _sim(example_gear, policy=PolicyName.MP_WASH_SHORTFALL)
    e = _sim(example_gear, policy=PolicyName.DEFERRED_MP_SHORTFALL, mp5_start_level=31)
    assert e.mp5_start_level == 31
    assert e.apr.total_apr == a.apr.total_apr == 1675
    assert e.apr.mp_wash_count == a.apr.mp_wash_count == 290
    assert e.apr.method1_hp_wash_count == a.apr.method1_hp_wash_count == 570
    assert e.apr.method2_hp_wash_count == a.apr.method2_hp_wash_count == 499
    assert e.apr.int_reset_apr == a.apr.int_reset_apr == 316
    assert e.final_display_hp == a.final_display_hp == 27016
    assert e.int_reached_level == a.int_reached_level == 67


@pytest.mark.regression
def test_regression_policy_e_late_mp5_matches_policy_b(example_gear):
    """mp5_start_level past early phase → shortfall always INT dump → like B."""
    b = _sim(example_gear, policy=PolicyName.INT_DUMP_SHORTFALL)
    e = _sim(example_gear, policy=PolicyName.DEFERRED_MP_SHORTFALL, mp5_start_level=200)
    assert e.apr.total_apr == b.apr.total_apr == 1665
    assert e.apr.mp_wash_count == b.apr.mp_wash_count == 275
    assert e.apr.method1_hp_wash_count == b.apr.method1_hp_wash_count == 545
    assert e.apr.method2_hp_wash_count == b.apr.method2_hp_wash_count == 529
    assert e.apr.int_reset_apr == b.apr.int_reset_apr == 316
    assert e.final_display_hp == b.final_display_hp == 27006


@pytest.mark.regression
def test_regression_policy_e_mid_start_between_a_and_b(example_gear):
    """Intermediate mp5_start should sit between pure A and pure B APR."""
    a = _sim(example_gear, policy=PolicyName.MP_WASH_SHORTFALL)
    b = _sim(example_gear, policy=PolicyName.INT_DUMP_SHORTFALL)
    e = _sim(example_gear, policy=PolicyName.DEFERRED_MP_SHORTFALL, mp5_start_level=55)
    assert e.apr.total_apr == 1668
    assert e.final_display_hp == 27010
    lo, hi = sorted([a.apr.total_apr, b.apr.total_apr])
    assert lo <= e.apr.total_apr <= hi


@pytest.mark.regression
def test_regression_mw_and_threshold_constants(example_gear):
    """MW 10% + thr 60 remain the defaults that reports / UI assume."""
    result = _sim(example_gear, policy=PolicyName.MP_WASH_SHORTFALL)
    assert result.extra_mp_threshold == 60
    assert_plan_invariants(result)
    # Level-up uses MW; wiping MW should change Extra MP trajectory / APR.
    no_mw = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=320,
            target_hp=27000,
            int_reset_level=155,
            int_gear=example_gear,
            mp_wash_end=120,
            hp_mode=HpMode.AVG,
            mw_percent=0.0,
            int_gear_after_reset=50,
        )
    )
    assert no_mw.apr.total_apr != result.apr.total_apr


@pytest.mark.regression
def test_regression_int_reset_apr_equals_peak_minus_four(example_gear):
    for policy in (
        PolicyName.MP_WASH_SHORTFALL,
        PolicyName.INT_DUMP_SHORTFALL,
        PolicyName.DEFERRED_MP_SHORTFALL,
        PolicyName.INT_ONLY_PLAIN,
        PolicyName.MP_WASH_HARDCORE,
    ):
        result = _sim(
            example_gear,
            policy=policy,
            target_base_int=280,
            target_hp=22000,
            mp_wash_end=110,
            mp5_start_level=50,
        )
        assert_plan_invariants(result)
        assert result.apr.int_reset_apr == result.base_int_peak - 4


@pytest.mark.regression
def test_regression_policy_b_shortfall_int5_has_zero_apr(example_gear):
    result = _sim(
        example_gear,
        policy=PolicyName.INT_DUMP_SHORTFALL,
        target_base_int=300,
        target_hp=24000,
    )
    int5 = [
        r
        for r in result.plan
        if r.action is Action.INT5 and 31 <= r.level <= result.int_reached_level
    ]
    assert int5
    assert all(r.apr_spent == 0 for r in int5)


@pytest.mark.regression
def test_regression_optimize_abe_winner_golden(example_gear):
    """Locked ABE optimize outcome for the user's gear / 27k / reset 155 scenario."""
    result = optimize(
        OptimizeConfig(
            target_hp=27000,
            int_reset_level=155,
            int_gear=example_gear,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.DEFERRED_MP_SHORTFALL,
            ],
            target_base_int_min=280,
            target_base_int_max=360,
            target_base_int_step=40,
            mp_wash_end_min=100,
            mp5_start_level_min=40,
            mp5_start_level_max=70,
            int_gear_after_reset=50,
            top_n=3,
        )
    )
    assert result.winner is not None
    assert result.winner.reached_target
    # Golden: B (or E tied) wins at 1560 APR with INT 360 / mpEnd 105.
    assert result.winner.total_apr == 1560
    assert result.winner.target_base_int == 360
    assert result.winner.mp_wash_end == 105
    assert result.comparison.policy_a is not None
    assert result.comparison.policy_a.total_apr == 1568
    assert result.comparison.policy_b is not None
    assert result.comparison.policy_b.total_apr == 1560
    assert result.comparison.policy_e is not None
    assert result.comparison.policy_e.total_apr == 1560
    assert result.comparison.policy_e.mp5_start_level == 70
    # B and E tie at 1560; runner-up is the other tied policy → delta 0 (not vs A).
    assert result.comparison.apr_delta == 0
    assert result.comparison.winner is result.winner

    report = format_optimize_report(result)
    assert policy_short(result.winner.policy) in {"B", "E"}
    assert "1560" in report


@pytest.mark.regression
def test_regression_policy_labels_stable():
    assert policy_short(PolicyName.DEFERRED_MP_SHORTFALL) == "E"
    assert "延遲 MP5" in policy_label(PolicyName.DEFERRED_MP_SHORTFALL)
    assert "不足時 MP wash" in policy_label(PolicyName.MP_WASH_SHORTFALL)
    assert "全點 INT" in policy_label(PolicyName.INT_DUMP_SHORTFALL)


@pytest.mark.regression
def test_regression_hp_mode_monotonic_apr(example_gear):
    """MAX rolls spend ≤ AVG ≤ MIN APR to hit the same display HP target."""
    avg = _sim(example_gear, policy=PolicyName.MP_WASH_SHORTFALL)
    by_mode = {HpMode.AVG: avg}
    for mode in (HpMode.MIN, HpMode.MAX):
        by_mode[mode] = simulate(
            SimulateConfig(
                policy=PolicyName.MP_WASH_SHORTFALL,
                target_base_int=320,
                target_hp=27000,
                int_reset_level=155,
                int_gear=example_gear,
                mp_wash_end=120,
                hp_mode=mode,
                int_gear_after_reset=50,
            )
        )
    assert by_mode[HpMode.MAX].apr.total_apr <= by_mode[HpMode.AVG].apr.total_apr
    assert by_mode[HpMode.AVG].apr.total_apr <= by_mode[HpMode.MIN].apr.total_apr
    for result in by_mode.values():
        assert result.reached_target
        assert result.final_display_hp >= 27000
