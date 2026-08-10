"""Hardcore Policy C: per-AP greedy HP1 / MP1 loop from level 10 until target INT.

From level 30 onward each fresh AP slot:
  1. If Extra MP >= 12 → Method 1 (HP1)
  2. Else try MP wash (MP1)
  3. Re-check after each wash; leftover AP → INT/LUK (0 APR)

Levels 10–29: step 2 is skipped (MP wash not allowed); leftover AP → INT/LUK.
"""

from __future__ import annotations

from dataclasses import dataclass

from hp_wash_thief.core import formulas as F
from hp_wash_thief.core.models import Action, HpMode, PolicyName

POLICY = PolicyName.MP_WASH_HARDCORE
EARLY_START_LEVEL = 10
MP_WASH_MIN_LEVEL = 30


@dataclass(frozen=True)
class GreedyStep:
    kind: str  # "HP" | "MP" | "INT"


@dataclass
class GreedyWashPlan:
    steps: list[GreedyStep]
    hp_washes: int = 0
    mp_washes: int = 0
    int_dump: int = 0


def plan_greedy_wash(
    *,
    base_int: int,
    base_mp: float,
    level: int,
    fresh_ap: int,
    allow_mp: bool,
    hp_mode: HpMode,
) -> GreedyWashPlan:
    """Pure planner mirroring simulator greedy loop (for tests)."""
    mp = float(base_mp)
    steps: list[GreedyStep] = []
    hp_washes = mp_washes = 0
    remaining = int(fresh_ap)

    while remaining > 0:
        if F.extra_mp(mp, level) >= F.MP_REMOVED_PER_APR:
            mp -= F.MP_REMOVED_PER_APR
            hp_washes += 1
            steps.append(GreedyStep("HP"))
            remaining -= 1
            continue
        if allow_mp:
            gain = F.fresh_ap_mp_gain(base_int, hp_mode)
            mp += gain
            if F.extra_mp(mp, level) >= F.MP_REMOVED_PER_APR:
                mp -= F.MP_REMOVED_PER_APR
                mp_washes += 1
                steps.append(GreedyStep("MP"))
                remaining -= 1
                continue
            mp -= gain
        break

    int_dump = remaining
    steps.extend(GreedyStep("INT") for _ in range(int_dump))
    return GreedyWashPlan(steps=steps, hp_washes=hp_washes, mp_washes=mp_washes, int_dump=int_dump)


def choose_level_action(level: int) -> Action:
    """Policy C early phase always uses per-AP greedy allocation."""
    del level
    return Action.HARDCORE_GREEDY
