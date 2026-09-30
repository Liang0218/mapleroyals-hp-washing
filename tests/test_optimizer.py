"""Optimizer smoke tests (narrow search grid)."""

from __future__ import annotations

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import OptimizeConfig, PolicyName, SimulateConfig
from hp_wash_thief.core.optimizer import _mp_wash_end_candidates
from hp_wash_thief.core.report import format_optimize_summary_text


GEAR = parse_int_gear(
    [
        {"from_level": 1, "to_level": 200, "int_gear": 100},
    ]
)


def test_optimize_abd_policies_narrow():
    result = optimize(
        OptimizeConfig(
            target_hp=22000,
            int_reset_level=140,
            int_gear=GEAR,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.INT_ONLY_PLAIN,
            ],
            target_base_int_min=200,
            target_base_int_max=280,
            target_base_int_step=40,
            mp_wash_end_min=70,
            extra_mp_threshold=60,
            top_n=3,
        )
    )
    assert result.winner is not None
    assert PolicyName.MP_WASH_SHORTFALL in result.by_policy
    assert PolicyName.INT_DUMP_SHORTFALL in result.by_policy
    assert PolicyName.INT_ONLY_PLAIN in result.by_policy
    assert result.comparison.winner is not None
    assert result.comparison.policy_c is None
    assert result.comparison.policy_d is not None
    assert result.winner.apr.total_apr == result.winner.total_apr
    assert result.winner.extra_mp_threshold == 60
    assert result.winner.int_reached_level > 0


def test_optimize_all_policies_abcd():
    result = optimize(
        OptimizeConfig(
            target_hp=22000,
            int_reset_level=140,
            int_gear=GEAR,
            target_base_int_min=200,
            target_base_int_max=280,
            target_base_int_step=40,
            mp_wash_end_min=70,
            top_n=3,
        )
    )
    assert PolicyName.MP_WASH_HARDCORE in result.by_policy
    assert PolicyName.INT_ONLY_PLAIN in result.by_policy
    assert result.comparison.policy_c is not None
    assert result.comparison.policy_d is not None
    assert result.comparison.winner is not None
    bests = [
        c
        for c in (
            result.comparison.policy_a,
            result.comparison.policy_b,
            result.comparison.policy_c,
            result.comparison.policy_d,
        )
        if c is not None
    ]
    assert result.comparison.winner in bests
    assert result.comparison.apr_delta is not None


def test_mp_wash_end_grid_includes_skip_sentinel():
    cfg = OptimizeConfig(
        target_hp=10000,
        int_reset_level=80,
        int_gear=GEAR,
    )
    assert cfg.mp_wash_end_min == 31
    values = _mp_wash_end_candidates(cfg, step=10)
    assert values[0] == 31


def test_optimize_skips_forced_mp_wash_to_50_when_unneeded():
    """Easy HP must not keep MP-washing through the old min 50 after INT lands."""
    result = optimize(
        OptimizeConfig(
            target_hp=8000,
            int_reset_level=120,
            int_gear=GEAR,
            policies=[PolicyName.INT_ONLY_PLAIN],
            target_base_int_min=140,
            target_base_int_max=180,
            target_base_int_step=40,
            top_n=3,
        )
    )
    assert result.winner is not None
    assert result.winner.reached_target
    assert result.winner.mp_wash_end < 50
    leftover_mp = [
        r
        for r in result.winner.plan
        if 32 <= r.level <= 50 and r.fresh_ap_mp > 0
    ]
    assert leftover_mp == []
    text = format_optimize_summary_text(result)
    if result.winner.mp_wash_end < result.winner.int_reached_level:
        assert "達標 INT 後不再 MP wash" in text

    forced = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=result.winner.target_base_int,
            target_hp=8000,
            int_reset_level=120,
            int_gear=GEAR,
            mp_wash_end=50,
        )
    )
    assert forced.apr.mp_wash_count > result.winner.apr.mp_wash_count
