"""MapleRoyals Thief HP/MP wash formulas.

Sources:
- https://royals.ms/forum/threads/night-lord-shadower-hp-washing-above-20k-hp.146816/
- https://royals.ms/forum/threads/hp-washing-for-new-players.41129/
"""

from __future__ import annotations

from hp_wash_thief.core.models import HpMode


def pick_range(low: float, high: float, mode: HpMode) -> float:
    if mode is HpMode.MIN:
        return float(low)
    if mode is HpMode.MAX:
        return float(high)
    return (float(low) + float(high)) / 2.0


def min_mp(level: int) -> int:
    """Thief minimum washable MP: (14 * level) + 148."""
    if level < 1:
        raise ValueError("level must be >= 1")
    return (14 * level) + 148


def extra_mp(base_mp: float, level: int) -> float:
    """Extra MP = base MP - min MP (equipment MP excluded)."""
    return float(base_mp) - float(min_mp(level))


def levelup_hp_gain(*, is_beginner: bool, mode: HpMode) -> float:
    """Natural HP gain on level-up (before fresh AP)."""
    if is_beginner:
        return pick_range(12, 16, mode)
    return pick_range(20, 24, mode)


def levelup_mp_base_gain(*, is_beginner: bool, mode: HpMode) -> float:
    """Natural MP gain on level-up before INT bonus."""
    if is_beginner:
        return pick_range(10, 12, mode)
    return pick_range(14, 16, mode)


def levelup_mp_int_bonus(total_int: int) -> int:
    """Level-up MP bonus from total INT (base + gear + MW%% of base): total_int // 10."""
    return max(0, int(total_int) // 10)


def fresh_ap_mp_gain(base_int: int, mode: HpMode) -> float:
    """Fresh AP into MP: (10-12) + base_int // 10. Gear/MW do not apply."""
    return pick_range(10, 12, mode) + (max(0, int(base_int)) // 10)


def method1_hp_gain(mode: HpMode) -> float:
    """Method 1 (fresh AP → HP): +20-24 HP; APR removes 12 MP."""
    return pick_range(20, 24, mode)


def method2_hp_gain(mode: HpMode) -> float:
    """Method 2 (APR MP → HP): +16-20 HP; -12 MP."""
    return pick_range(16, 20, mode)


MP_REMOVED_PER_APR = 12
# Full level HP wash×5 needs Extra MP ≥ 12 × 5.
EXTRA_MP_THRESHOLD_DEFAULT = MP_REMOVED_PER_APR * 5  # 60



def job_advance_bonus(job_adv_number: int, mode: HpMode) -> tuple[float, float]:
    """Return (hp, mp) granted on job advancement.

    job_adv_number: 1 for Rogue, 2 for Assassin/Bandit, 3 for Hermit/Chief Bandit,
    4 for Night Lord / Shadower.
    """
    if job_adv_number == 1:
        # Guide lists 162.5; treat as fixed midpoint (range ±50 historically).
        if mode is HpMode.MIN:
            return 112.5, 0.0
        if mode is HpMode.MAX:
            return 212.5, 0.0
        return 162.5, 0.0
    if job_adv_number in (2, 3, 4):
        if mode is HpMode.MIN:
            return 275.0, 125.0
        if mode is HpMode.MAX:
            return 375.0, 225.0
        return 325.0, 175.0
    raise ValueError(f"unsupported job advancement: {job_adv_number}")


def job_advance_ap(job_adv_number: int) -> int:
    """Bonus AP granted on job advancement (MapleRoyals v83).

    Source: https://royals.ms/forum/threads/2nd-3rd-4th-job-bonuses.45500/
    1st/2nd job: 0 AP; 3rd/4th job: 5 AP each.
    """
    if job_adv_number in (3, 4):
        return 5
    return 0


# Job advance levels for Thief line.
JOB_ADVANCE_LEVELS = {
    10: 1,
    30: 2,
    70: 3,
    120: 4,
}

FRESH_AP_PER_LEVEL = 5

STARTING_HP = 50.0
STARTING_MP = 5.0
STARTING_STR = 4
STARTING_DEX = 4
STARTING_INT = 4
STARTING_LUK = 4
# PerfectSin guide: character creation grants 9 fresh AP.
STARTING_FRESH_AP = 9
FIRST_JOB_DEX_REQUIREMENT = 25
BASE_STAT_FLOOR = 4
