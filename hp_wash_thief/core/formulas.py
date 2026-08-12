"""MapleRoyals HP/MP wash formulas (job-aware; Thief defaults preserved).

Sources:
- https://royals.ms/forum/threads/night-lord-shadower-hp-washing-above-20k-hp.146816/
- https://royals.ms/forum/threads/hp-washing-for-new-players.41129/
"""

from __future__ import annotations

from typing import Union

from hp_wash_thief.core.models import HpMode


def pick_range(low: float, high: float, mode: HpMode) -> float:
    if mode is HpMode.MIN:
        return float(low)
    if mode is HpMode.MAX:
        return float(high)
    return (float(low) + float(high)) / 2.0


def min_mp(level: int, job: Union[str, object] = "thief") -> int:
    """Minimum washable MP for ``job`` (default: Thief ``14*level+148``)."""
    from hp_wash_thief.core.jobs import get_job_profile

    return get_job_profile(job).min_mp(level)


def extra_mp(base_mp: float, level: int, job: Union[str, object] = "thief") -> float:
    """Extra MP = base MP - min MP (equipment MP excluded)."""
    from hp_wash_thief.core.jobs import get_job_profile

    return get_job_profile(job).extra_mp(base_mp, level)


def levelup_hp_gain(*, is_beginner: bool, mode: HpMode) -> float:
    """Natural HP gain on level-up (Thief/legacy helper; prefer JobProfile)."""
    if is_beginner:
        return pick_range(12, 16, mode)
    return pick_range(20, 24, mode)


def levelup_mp_base_gain(*, is_beginner: bool, mode: HpMode) -> float:
    """Natural MP gain on level-up before INT bonus (Thief/legacy helper)."""
    if is_beginner:
        return pick_range(10, 12, mode)
    return pick_range(14, 16, mode)


def levelup_mp_int_bonus(total_int: int) -> int:
    """Level-up MP bonus from total INT (base + gear + MW%% of base): total_int // 10."""
    return max(0, int(total_int) // 10)


def fresh_ap_mp_gain(base_int: int, mode: HpMode, job: Union[str, object] = "thief") -> float:
    """Fresh AP into MP. Gear/MW do not apply."""
    from hp_wash_thief.core.jobs import get_job_profile

    return get_job_profile(job).fresh_ap_mp(base_int, mode)


def method1_hp_gain(mode: HpMode, job: Union[str, object] = "thief", *, ap_hp_bonus: int = 0) -> float:
    """Method 1 (fresh AP → HP) base + optional Improve MaxHP AP bonus."""
    from hp_wash_thief.core.jobs import get_job_profile

    return get_job_profile(job).method1_base.pick(mode) + ap_hp_bonus


def method2_hp_gain(mode: HpMode, job: Union[str, object] = "thief", *, ap_hp_bonus: int = 0) -> float:
    """Method 2 (APR MP → HP) base + optional Improve MaxHP AP bonus."""
    from hp_wash_thief.core.jobs import get_job_profile

    return get_job_profile(job).method2_base.pick(mode) + ap_hp_bonus


# Thief defaults (backward compatible module constants).
MP_REMOVED_PER_APR = 12
EXTRA_MP_THRESHOLD_DEFAULT = MP_REMOVED_PER_APR * 5  # 60


def method1_washes_affordable(
    extra_mp_value: float, fresh_ap: int, *, mp_removed_per_apr: int = MP_REMOVED_PER_APR
) -> int:
    """How many Method 1 washes fit in Extra MP and fresh AP this level."""
    if extra_mp_value < mp_removed_per_apr or fresh_ap <= 0:
        return 0
    return min(int(fresh_ap), int(extra_mp_value // mp_removed_per_apr))


def mp_washes_affordable(
    base_int: int,
    base_mp: float,
    level: int,
    fresh_ap: int,
    *,
    mode: HpMode,
    job: Union[str, object] = "thief",
) -> int:
    """How many MP washes succeed this level (simulate add-then-remove per fresh AP)."""
    from hp_wash_thief.core.jobs import get_job_profile

    if fresh_ap <= 0:
        return 0
    profile = get_job_profile(job)
    mp = float(base_mp)
    done = 0
    removed = profile.mp_removed_per_apr
    for _ in range(fresh_ap):
        gain = profile.fresh_ap_mp(base_int, mode)
        mp += gain
        if profile.extra_mp(mp, level) < removed:
            mp -= gain
            break
        mp -= removed
        done += 1
    return done


def job_advance_bonus(job_adv_number: int, mode: HpMode) -> tuple[float, float]:
    """Thief-line job advance bonuses (legacy helper)."""
    if job_adv_number == 1:
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
    """Bonus AP granted on job advancement (MapleRoyals v83)."""
    if job_adv_number in (3, 4):
        return 5
    return 0


# Job advance levels for Thief line (legacy).
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
STARTING_FRESH_AP = 9
FIRST_JOB_DEX_REQUIREMENT = 25
BASE_STAT_FLOOR = 4
