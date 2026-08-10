"""Early-phase shortfall policy: dump 5 fresh AP into INT (0 wash APR that level)."""

from __future__ import annotations

from hp_wash_thief.core.models import Action, PolicyName

POLICY = PolicyName.INT_DUMP_SHORTFALL


def choose_early_action(extra_mp_value: float, threshold: int, *, fresh_ap: int = 5) -> Action:
    """Return HP5 when Extra MP >= threshold, otherwise INT5 (or LUK5 if INT capped)."""
    del fresh_ap
    if extra_mp_value >= threshold:
        return Action.HP5
    return Action.INT5
