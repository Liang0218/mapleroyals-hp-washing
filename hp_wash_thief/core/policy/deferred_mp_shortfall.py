"""Policy E: hybrid A/B — defer MP5 until mp5_start_level.

When Extra MP >= threshold → HP wash×5 (same as A/B).
When Extra MP < threshold:
  - level < mp5_start_level → dump 5 AP into INT (like B)
  - level >= mp5_start_level → MP wash×5 (like A)
"""

from __future__ import annotations

from hp_wash_thief.core.models import Action, PolicyName

POLICY = PolicyName.DEFERRED_MP_SHORTFALL


def choose_early_action(
    extra_mp_value: float,
    threshold: int,
    *,
    level: int,
    mp5_start_level: int,
    fresh_ap: int = 5,
) -> Action:
    del fresh_ap
    if extra_mp_value >= threshold:
        return Action.HP5
    if level < mp5_start_level:
        return Action.INT5
    return Action.MP5
