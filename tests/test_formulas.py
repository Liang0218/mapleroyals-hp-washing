"""Unit tests for wash formulas."""

from __future__ import annotations

import pytest

from hp_wash_thief.core.formulas import (
    MP_REMOVED_PER_APR,
    extra_mp,
    fresh_ap_mp_gain,
    job_advance_ap,
    job_advance_bonus,
    levelup_hp_gain,
    levelup_mp_base_gain,
    levelup_mp_int_bonus,
    method1_hp_gain,
    method1_washes_affordable,
    method2_hp_gain,
    min_mp,
)
from hp_wash_thief.core.models import HpMode


def test_min_mp_formula():
    assert min_mp(34) == (14 * 34) + 148
    assert min_mp(1) == 162
    assert min_mp(200) == 2948


def test_extra_mp_example_from_guide():
    # PerfectSin: level 34, 700 base MP → Extra MP 76
    assert extra_mp(700, 34) == 76


def test_method1_washes_affordable():
    assert method1_washes_affordable(12, 5) == 1
    assert method1_washes_affordable(11, 5) == 0
    assert method1_washes_affordable(76, 5) == 5
    assert method1_washes_affordable(76, 10) == 6


def test_mp_washes_affordable():
    from hp_wash_thief.core.formulas import min_mp, mp_washes_affordable

    level = 30
    base_mp = float(min_mp(level) + 11)
    count = mp_washes_affordable(200, base_mp, level, 5, mode=HpMode.AVG)
    assert count >= 1
    assert count <= 5


def test_mp_removed_constant():
    assert MP_REMOVED_PER_APR == 12


@pytest.mark.parametrize(
    "mode,expected",
    [
        (HpMode.MIN, 20),
        (HpMode.AVG, 22),
        (HpMode.MAX, 24),
    ],
)
def test_method1_hp(mode, expected):
    assert method1_hp_gain(mode) == expected


@pytest.mark.parametrize(
    "mode,expected",
    [
        (HpMode.MIN, 16),
        (HpMode.AVG, 18),
        (HpMode.MAX, 20),
    ],
)
def test_method2_hp(mode, expected):
    assert method2_hp_gain(mode) == expected


def test_fresh_ap_mp_uses_base_int_only():
    # 300 base INT → +30 from INT, +11 avg base = 41
    assert fresh_ap_mp_gain(300, HpMode.AVG) == 11 + 30


def test_levelup_mp_int_bonus_uses_total_int():
    assert levelup_mp_int_bonus(352) == 35
    assert levelup_mp_int_bonus(9) == 0


def test_beginner_and_thief_levelup_ranges():
    assert levelup_hp_gain(is_beginner=True, mode=HpMode.AVG) == 14
    assert levelup_hp_gain(is_beginner=False, mode=HpMode.AVG) == 22
    assert levelup_mp_base_gain(is_beginner=True, mode=HpMode.AVG) == 11
    assert levelup_mp_base_gain(is_beginner=False, mode=HpMode.AVG) == 15


def test_job_advance_bonuses():
    assert job_advance_bonus(1, HpMode.AVG) == (162.5, 0.0)
    assert job_advance_bonus(2, HpMode.AVG) == (325.0, 175.0)
    assert job_advance_bonus(4, HpMode.AVG) == (325.0, 175.0)


def test_job_advance_ap():
    assert job_advance_ap(1) == 0
    assert job_advance_ap(2) == 0
    assert job_advance_ap(3) == 5
    assert job_advance_ap(4) == 5
