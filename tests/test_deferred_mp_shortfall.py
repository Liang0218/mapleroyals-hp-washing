"""Policy E deferred MP shortfall tests."""

from __future__ import annotations

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import Action, OptimizeConfig, PolicyName, SimulateConfig
from hp_wash_thief.core.policy.deferred_mp_shortfall import choose_early_action


GEAR = parse_int_gear([{"from_level": 1, "to_level": 200, "int_gear": 100}])


def test_deferred_policy_switches_at_mp5_start():
    assert choose_early_action(70, 60, level=40, mp5_start_level=50) is Action.HP5
    assert choose_early_action(40, 60, level=40, mp5_start_level=50) is Action.INT5
    assert choose_early_action(40, 60, level=50, mp5_start_level=50) is Action.MP5
    assert choose_early_action(40, 60, level=70, mp5_start_level=50) is Action.MP5


def test_simulate_deferred_uses_int_then_mp():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.DEFERRED_MP_SHORTFALL,
            target_base_int=280,
            target_hp=20000,
            int_reset_level=140,
            int_gear=GEAR,
            mp_wash_end=120,
            mp5_start_level=55,
            extra_mp_threshold=60,
        )
    )
    assert result.mp5_start_level == 55
    assert result.int_reached_level > 0
    # Before mp5_start, shortfall rows should be INT5 (or HP5 when enough MP).
    early_shortfall = [
        r
        for r in result.plan
        if 31 <= r.level < 55 and r.action in {Action.INT5, Action.MP5, Action.HP5, Action.LUK5}
    ]
    assert early_shortfall
    assert all(r.action is not Action.MP5 for r in early_shortfall)


def test_optimize_includes_policy_e():
    result = optimize(
        OptimizeConfig(
            target_hp=20000,
            int_reset_level=130,
            int_gear=GEAR,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.DEFERRED_MP_SHORTFALL,
            ],
            target_base_int_min=200,
            target_base_int_max=280,
            target_base_int_step=40,
            mp_wash_end_min=80,
            mp5_start_level_min=40,
            mp5_start_level_max=70,
            top_n=3,
        )
    )
    assert PolicyName.DEFERRED_MP_SHORTFALL in result.by_policy
    assert result.comparison.policy_e is not None or result.by_policy[
        PolicyName.DEFERRED_MP_SHORTFALL
    ].best is not None
    assert result.winner is not None
