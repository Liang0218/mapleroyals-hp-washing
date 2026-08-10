"""Policy D (int-only plain) tests."""

from __future__ import annotations

from hp_wash_thief.core.api import simulate
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import Action, HpMode, PolicyName, SimulateConfig


GEAR = parse_int_gear([{"from_level": 1, "to_level": 200, "int_gear": 100}])


def test_plain_policy_early_phase_only_int():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=200,
            target_hp=18000,
            int_reset_level=140,
            int_gear=GEAR,
            mp_wash_end=100,
        )
    )
    assert result.int_reached_level > 0
    for row in result.plan:
        if row.level > 30 and row.level < result.int_reached_level:
            assert row.action is Action.INT5
        if row.level > result.int_reached_level and row.level <= 100:
            assert row.action in (
                Action.MP5,
                Action.MP1,
                Action.MP2,
                Action.MP3,
                Action.MP4,
            )


def test_plain_policy_no_early_hp_wash():
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=240,
            target_hp=15000,
            int_reset_level=140,
            int_gear=GEAR,
            mp_wash_end=100,
            hp_mode=HpMode.MAX,
        )
    )
    early_wash = [
        r
        for r in result.plan
        if 31 <= r.level < result.int_reached_level and r.apr_spent > 0
    ]
    assert early_wash == []
