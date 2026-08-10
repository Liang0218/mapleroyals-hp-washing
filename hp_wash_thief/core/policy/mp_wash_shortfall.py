"""Early-phase shortfall policy: MP wash when Extra MP is below threshold (PerfectSin)."""

from __future__ import annotations

from hp_wash_thief.core.models import Action, PolicyName

POLICY = PolicyName.MP_WASH_SHORTFALL


def choose_early_action(extra_mp_value: float, threshold: int) -> Action:
    """Return HP5 when Extra MP >= threshold, otherwise MP5."""
    if extra_mp_value >= threshold:
        return Action.HP5
    return Action.MP5
