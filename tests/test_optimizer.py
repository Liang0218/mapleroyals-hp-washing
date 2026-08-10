"""Optimizer smoke tests (narrow search grid)."""

from __future__ import annotations

from hp_wash_thief.core.api import optimize
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import OptimizeConfig, PolicyName


GEAR = parse_int_gear(
    [
        {"from_level": 1, "to_level": 200, "int_gear": 100, "mw_int": 20},
    ]
)


def test_optimize_both_policies_narrow():
    result = optimize(
        OptimizeConfig(
            target_hp=22000,
            int_reset_level=140,
            int_gear=GEAR,
            policies=[PolicyName.MP_WASH_SHORTFALL, PolicyName.INT_DUMP_SHORTFALL],
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
    assert result.comparison.winner is not None
    assert result.winner.apr.total_apr == result.winner.total_apr
    assert result.winner.extra_mp_threshold == 60
    assert result.winner.int_reached_level > 0
