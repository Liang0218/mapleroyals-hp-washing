"""Policy helpers."""

from __future__ import annotations

from hp_wash_thief.core.models import Action, PolicyName
from hp_wash_thief.core.policy import int_dump_shortfall, mp_wash_shortfall


def choose_early_action(
    policy: PolicyName, extra_mp_value: float, threshold: int
) -> Action:
    if policy is PolicyName.MP_WASH_SHORTFALL:
        return mp_wash_shortfall.choose_early_action(extra_mp_value, threshold)
    if policy is PolicyName.INT_DUMP_SHORTFALL:
        return int_dump_shortfall.choose_early_action(extra_mp_value, threshold)
    raise ValueError(f"unknown policy: {policy}")
