"""Multi-job profiles, Improve MaxHP skill schedule, and non-Thief optimize."""

from __future__ import annotations

import pytest

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.formulas import (
    extra_mp,
    method1_hp_gain,
    method2_hp_gain,
    min_mp,
)
from hp_wash_thief.core.jobs import (
    JobId,
    SkillTracker,
    get_job_profile,
    make_skill_tracker,
)
from hp_wash_thief.core.models import (
    HpMode,
    IntGearSegment,
    OptimizeConfig,
    PolicyName,
    SimulateConfig,
)


def _gear() -> list[IntGearSegment]:
    return [IntGearSegment(from_level=1, to_level=200, int_gear=30)]


@pytest.mark.parametrize(
    "job,level,expected",
    [
        (JobId.THIEF, 50, 14 * 50 + 148),
        (JobId.BOWMAN, 50, 14 * 50 + 148),
        (JobId.GUNSLINGER, 50, 18 * 50 + 111),
        (JobId.BRAWLER, 50, 18 * 50 + 111),
        (JobId.FIGHTER, 50, 4 * 50 + 56),
        (JobId.PAGE, 50, 4 * 50 + 56),
        (JobId.SPEARMAN, 50, 4 * 50 + 156),
        (JobId.BEGINNER, 50, 10 * 50 + 2),
    ],
)
def test_min_mp_formulas(job, level, expected):
    assert min_mp(level, job) == expected
    assert get_job_profile(job).min_mp(level) == expected


def test_extra_mp_uses_job_min():
    assert extra_mp(1000, 50, JobId.FIGHTER) == 1000 - (4 * 50 + 56)
    assert extra_mp(1000, 50, JobId.THIEF) == 1000 - (14 * 50 + 148)


def test_method_gains_include_skill_bonus():
    assert method1_hp_gain(HpMode.AVG, JobId.FIGHTER, ap_hp_bonus=0) == 22
    assert method1_hp_gain(HpMode.AVG, JobId.FIGHTER, ap_hp_bonus=30) == 52
    assert method2_hp_gain(HpMode.AVG, JobId.BRAWLER, ap_hp_bonus=20) == 40


def test_warrior_skill_sp_schedule_fills_maxhp():
    profile = get_job_profile(JobId.FIGHTER)
    skill = make_skill_tracker(profile)
    # Unlock at 1st job (lv 10)
    skill.on_job_advance(1)
    for lv in range(10, 15):
        skill.on_level(lv, adv_number=1)
    # prereq 5 + 10 skill levels = 15 SP; 5 levels × 3 SP = 15
    assert skill.effective_level == 10
    assert skill.ap_hp_bonus() == 30
    assert skill.levelup_hp_bonus() == 40


def test_brawler_skill_unlocks_at_second_job():
    profile = get_job_profile(JobId.BRAWLER)
    skill = make_skill_tracker(profile)
    skill.on_job_advance(1)
    skill.on_level(10, adv_number=1)
    assert skill.effective_level == 0
    skill.on_job_advance(2)
    for lv in range(30, 34):
        skill.on_level(lv, adv_number=2)
    assert skill.effective_level == 10
    assert skill.ap_hp_bonus() == 20


def test_skill_override_freezes_level():
    profile = get_job_profile(JobId.FIGHTER)
    skill = make_skill_tracker(profile, override_level=7)
    skill.on_job_advance(1)
    for lv in range(10, 40):
        skill.on_level(lv, adv_number=1)
    assert skill.effective_level == 7
    assert skill.ap_hp_bonus() == 21


def test_beginner_has_no_job_advances():
    profile = get_job_profile(JobId.BEGINNER)
    assert profile.job_advances == {}
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=120,
            target_hp=8000,
            int_reset_level=100,
            int_gear=_gear(),
            job=JobId.BEGINNER,
            mp_wash_end=80,
        )
    )
    assert result.job == JobId.BEGINNER.value
    for row in result.plan:
        if row.level in (70, 120):
            spent = (
                row.fresh_ap_int
                + row.fresh_ap_luk
                + row.fresh_ap_dex
                + row.fresh_ap_str
                + row.fresh_ap_hp
                + row.fresh_ap_mp
            )
            assert spent == 5, f"beginner lv{row.level} should not get job-advance AP"


def test_non_thief_optimize_d_only():
    result = optimize(
        OptimizeConfig(
            target_hp=12000,
            int_reset_level=120,
            int_gear=_gear(),
            job=JobId.BOWMAN,
            target_base_int_min=100,
            target_base_int_max=160,
            target_base_int_step=20,
            mp_wash_end_min=70,
            top_n=3,
        )
    )
    assert list(result.by_policy.keys()) == [PolicyName.INT_ONLY_PLAIN]
    assert result.winner is not None
    assert result.winner.policy is PolicyName.INT_ONLY_PLAIN
    assert result.winner.job == JobId.BOWMAN.value


def test_fighter_maxhp_monotonic_method2():
    # High target so plans keep washing; skill bonus should raise final HP.
    hps = []
    for lv in (0, 5, 10):
        r = simulate(
            SimulateConfig(
                policy=PolicyName.INT_ONLY_PLAIN,
                target_base_int=150,
                target_hp=999999,
                int_reset_level=130,
                int_gear=_gear(),
                job=JobId.FIGHTER,
                mp_wash_end=100,
                improved_maxhp_level=lv,
            )
        )
        hps.append(r.final_base_hp)
    assert hps[0] < hps[1] < hps[2]


def test_brawler_maxhp_monotonic_method2():
    low = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=150,
            target_hp=999999,
            int_reset_level=130,
            int_gear=_gear(),
            job=JobId.BRAWLER,
            mp_wash_end=100,
            improved_maxhp_level=0,
        )
    )
    high = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=150,
            target_hp=999999,
            int_reset_level=130,
            int_gear=_gear(),
            job=JobId.BRAWLER,
            mp_wash_end=100,
            improved_maxhp_level=10,
        )
    )
    assert high.final_base_hp > low.final_base_hp


def test_thief_still_runs_abcd():
    result = optimize(
        OptimizeConfig(
            target_hp=15000,
            int_reset_level=120,
            int_gear=_gear(),
            job=JobId.THIEF,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.MP_WASH_HARDCORE,
                PolicyName.INT_ONLY_PLAIN,
            ],
            target_base_int_min=120,
            target_base_int_max=180,
            target_base_int_step=30,
            mp_wash_end_min=80,
            top_n=2,
        )
    )
    assert set(result.by_policy.keys()) == {
        PolicyName.MP_WASH_SHORTFALL,
        PolicyName.INT_DUMP_SHORTFALL,
        PolicyName.MP_WASH_HARDCORE,
        PolicyName.INT_ONLY_PLAIN,
    }


def test_gunslinger_mp_removed():
    assert get_job_profile(JobId.GUNSLINGER).mp_removed_per_apr == 16
    assert get_job_profile(JobId.GUNSLINGER).prefer_method2 is True


def test_skill_tracker_seed_resume():
    profile = get_job_profile(JobId.FIGHTER)
    skill = SkillTracker(spec=profile.maxhp_skill)
    advances = {lv: adv for lv, (adv, _) in profile.job_advances.items()}
    skill.seed_for_resume(20, advances)
    assert skill.unlocked
    assert skill.effective_level == 10
