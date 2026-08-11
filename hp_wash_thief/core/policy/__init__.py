"""Policy helpers."""

from __future__ import annotations

from hp_wash_thief.core.models import Action, HpMode, PolicyName
from hp_wash_thief.core.policy import (
    deferred_mp_shortfall,
    int_dump_shortfall,
    mp_wash_hardcore,
    mp_wash_shortfall,
)


def choose_early_action(
    policy: PolicyName,
    extra_mp_value: float,
    threshold: int,
    *,
    level: int = 31,
    fresh_ap: int = 5,
    base_int: int = 4,
    base_mp: float = 0.0,
    hp_mode: HpMode = HpMode.AVG,
    mp5_start_level: int = 50,
) -> Action:
    if policy is PolicyName.MP_WASH_HARDCORE:
        return mp_wash_hardcore.choose_level_action(level)
    if policy is PolicyName.MP_WASH_SHORTFALL:
        return mp_wash_shortfall.choose_early_action(extra_mp_value, threshold, fresh_ap=fresh_ap)
    if policy is PolicyName.INT_DUMP_SHORTFALL:
        return int_dump_shortfall.choose_early_action(extra_mp_value, threshold, fresh_ap=fresh_ap)
    if policy is PolicyName.DEFERRED_MP_SHORTFALL:
        return deferred_mp_shortfall.choose_early_action(
            extra_mp_value,
            threshold,
            level=level,
            mp5_start_level=mp5_start_level,
            fresh_ap=fresh_ap,
        )
    raise ValueError(f"unknown policy: {policy}")
