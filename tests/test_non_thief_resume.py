"""Non-thief mid-game resume correctness."""

from __future__ import annotations

import pytest

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.jobs import JobId, get_job_profile, make_skill_tracker
from hp_wash_thief.core.models import (
    Action,
    IntGearSegment,
    OptimizeConfig,
    PolicyName,
    ResumeFrom,
    SimulateConfig,
)
from hp_wash_thief.core.simulator import (
    CharacterState,
    _apply_starting_ap,
    _decide_action,
    _execute_action,
    _level_up,
    _maybe_mark_int_reached,
    _maybe_reset_int,
    _method2_top_up,
    _reset_int_to_floor,
)
from hp_wash_thief.core import formulas as F
from hp_wash_thief.core.report import format_optimize_summary_text


def _gear() -> list[IntGearSegment]:
    return [IntGearSegment(from_level=1, to_level=200, int_gear=30)]


def _cfg(job: str, **kw) -> SimulateConfig:
    return SimulateConfig(
        policy=PolicyName.INT_ONLY_PLAIN,
        target_base_int=kw.get("target_base_int", 250),
        target_hp=kw.get("target_hp", 28000),
        int_reset_level=kw.get("int_reset_level", 155),
        int_gear=_gear(),
        job=job,
        mp_wash_end=kw.get("mp_wash_end", 120),
        improved_maxhp_level=kw.get("improved_maxhp_level"),
    )


def _snapshot_before_action(job: str, resume_level: int, **kw) -> tuple[CharacterState, SimulateConfig]:
    cfg = _cfg(job, **kw)
    if get_job_profile(job).maxhp_skill and cfg.improved_maxhp_level is None:
        cfg.improved_maxhp_level = 10
    profile = get_job_profile(job)
    skill = make_skill_tracker(profile, override_level=cfg.improved_maxhp_level)
    state = CharacterState(profile=profile, skill=skill)
    _apply_starting_ap(state, cfg)
    _maybe_mark_int_reached(state, cfg)
    for new_level in range(2, resume_level + 1):
        _level_up(state, new_level, cfg)
        if new_level < resume_level:
            action = _decide_action(state, cfg)
            _execute_action(state, action, cfg)
            _maybe_mark_int_reached(state, cfg)
            _maybe_reset_int(state, cfg)
    return state, cfg


def _finish_remaining_apr(state: CharacterState, cfg: SimulateConfig) -> int:
    start = (
        state.mp_wash_count
        + state.method1_hp_wash_count
        + state.method2_hp_wash_count
        + state.int_reset_apr
    )
    action = _decide_action(state, cfg)
    _execute_action(state, action, cfg)
    _maybe_mark_int_reached(state, cfg)
    _maybe_reset_int(state, cfg)
    for new_level in range(state.level + 1, cfg.max_level + 1):
        _level_up(state, new_level, cfg)
        action = _decide_action(state, cfg)
        _execute_action(state, action, cfg)
        _maybe_mark_int_reached(state, cfg)
        _maybe_reset_int(state, cfg)
    if cfg.auto_method2:
        _method2_top_up(state, cfg)
    if not state.int_reset_done and state.base_int > F.BASE_STAT_FLOOR:
        _reset_int_to_floor(state, cfg)
    end = (
        state.mp_wash_count
        + state.method1_hp_wash_count
        + state.method2_hp_wash_count
        + state.int_reset_apr
    )
    return end - start


@pytest.mark.parametrize("job", ["fighter", "bowman", "brawler", "gunslinger"])
@pytest.mark.parametrize("level", [40, 80, 100])
def test_non_thief_resume_matches_continued_sim(job, level):
    state, cfg = _snapshot_before_action(job, level)
    rem = _finish_remaining_apr(_snapshot_before_action(job, level)[0], cfg)
    state2, cfg2 = _snapshot_before_action(job, level)
    resume = ResumeFrom(
        level=state2.level,
        base_hp=state2.base_hp,
        base_mp=state2.base_mp,
        base_int=state2.base_int,
        base_luk=state2.base_luk,
        base_dex=state2.base_dex,
        base_str=state2.base_str,
        fresh_ap=state2.level_fresh_ap,
        int_reset_done=state2.int_reset_done,
        base_int_peak=state2.base_int_peak,
    )
    result = simulate(
        SimulateConfig(
            policy=cfg2.policy,
            target_base_int=cfg2.target_base_int,
            target_hp=cfg2.target_hp,
            int_reset_level=cfg2.int_reset_level,
            int_gear=cfg2.int_gear,
            job=cfg2.job,
            mp_wash_end=cfg2.mp_wash_end,
            improved_maxhp_level=cfg2.improved_maxhp_level,
            resume_from=resume,
        )
    )
    assert result.apr.total_apr == rem
    assert result.plan[0].action is Action.RESUME


def test_fighter_resume_auto_maxhp_from_sp_schedule():
    """Leave improved_maxhp_level unset → seed from unlock with prereq-first SP."""
    resume = ResumeFrom.from_stats(
        level=70,
        base_hp=12000,
        base_mp=get_job_profile(JobId.FIGHTER).min_mp(70) + 200,
        base_int=180,
        base_str=50,
        job="fighter",
    )
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=220,
            target_hp=25000,
            int_reset_level=155,
            int_gear=_gear(),
            job="fighter",
            mp_wash_end=120,
            resume_from=resume,
            # no improved_maxhp_level → auto
        )
    )
    # Warrior unlocks at lv10; 5 prereq + 10 skill = 15 SP → 5 levels × 3 SP → full by lv14
    assert result.improved_maxhp_level == 10
    assert "依SP自動" in result.plan[0].notes


def test_fighter_resume_maxhp_partial_before_full():
    """At level 12, auto schedule should not yet be MaxHP 10."""
    profile = get_job_profile(JobId.FIGHTER)
    skill = make_skill_tracker(profile)
    advances = {lv: adv for lv, (adv, _) in profile.job_advances.items()}
    skill.seed_for_resume(12, advances)
    # lv10–12 = 3 levels × 3 SP = 9 → prereq 5 + skill 4
    assert skill.prereq_spent == 5
    assert skill.effective_level == 4


def test_brawler_resume_auto_maxhp_unlocks_at_second_job():
    resume = ResumeFrom.from_stats(
        level=35,
        base_hp=8000,
        base_mp=get_job_profile(JobId.BRAWLER).min_mp(35) + 100,
        base_int=120,
        base_str=40,
        base_dex=20,
        job="brawler",
    )
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=150,
            target_hp=18000,
            int_reset_level=130,
            int_gear=_gear(),
            job="brawler",
            mp_wash_end=100,
            resume_from=resume,
        )
    )
    # 2nd job at 30; no prereq; 10 SP → full by lv33; at 35 → 10
    assert result.improved_maxhp_level == 10


def test_fighter_resume_rejects_base_mp_below_min():
    floor = get_job_profile(JobId.FIGHTER).min_mp(70)
    resume = ResumeFrom.from_stats(
        level=70,
        base_hp=12000,
        base_mp=floor - 1,
        base_int=180,
        base_str=50,
        job="fighter",
    )
    with pytest.raises(ValueError, match="resume base_mp below job min_mp"):
        simulate(
            SimulateConfig(
                policy=PolicyName.INT_ONLY_PLAIN,
                target_base_int=220,
                target_hp=25000,
                int_reset_level=155,
                int_gear=_gear(),
                job="fighter",
                mp_wash_end=120,
                resume_from=resume,
            )
        )


def test_extra_mp_from_stats_uses_job_min_mp():
    level = 80
    extra = 400
    wrong = ResumeFrom.from_stats(
        level=level, base_hp=10000, extra_mp=extra, base_int=200, job="thief"
    )
    right = ResumeFrom.from_stats(
        level=level, base_hp=10000, extra_mp=extra, base_int=200, job="fighter"
    )
    assert wrong.base_mp == pytest.approx(get_job_profile("thief").min_mp(level) + extra)
    assert right.base_mp == pytest.approx(get_job_profile("fighter").min_mp(level) + extra)
    assert wrong.base_mp != right.base_mp


def test_bowman_resume_after_int_uses_dex_not_hp5():
    resume = ResumeFrom.from_stats(
        level=100,
        base_hp=16000,
        base_mp=get_job_profile(JobId.BOWMAN).min_mp(100) + 500,
        base_int=300,
        base_dex=120,
        job="bowman",
    )
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=300,
            target_hp=22000,
            int_reset_level=155,
            int_gear=_gear(),
            job="bowman",
            mp_wash_end=90,  # already past → primary dump
            resume_from=resume,
        )
    )
    actions = {r.action for r in result.plan if r.action is not Action.RESUME}
    assert Action.DEX5 in actions
    assert Action.HP5 not in actions


def test_optimize_resume_labels_stop_mp_wash():
    resume = ResumeFrom.from_stats(
        level=70,
        base_hp=12000,
        base_mp=get_job_profile(JobId.FIGHTER).min_mp(70) + 350,
        base_int=180,
        base_str=60,
        fresh_ap=10,
        job="fighter",
    )
    result = optimize(
        OptimizeConfig(
            target_hp=30000,
            int_reset_level=155,
            int_gear=_gear(),
            job="fighter",
            resume_from=resume,
            # auto MaxHP from SP
            target_base_int_min=180,
            target_base_int_max=260,
            target_base_int_step=40,
            mp_wash_end_min=50,
            top_n=3,
        )
    )
    assert result.winner is not None
    text = format_optimize_summary_text(result)
    if result.winner.mp_wash_end < resume.level:
        assert "不再 MP wash" in text
    assert "Extra MP≈350" in text or "Extra MP≈" in text
    # Must not show thief-scale negative Extra MP for fighter base_mp
    assert "Extra MP≈-" not in text
    assert result.winner.improved_maxhp_level == 10


def test_resume_maxhp_override_still_works():
    resume = ResumeFrom.from_stats(
        level=70,
        base_hp=12000,
        base_mp=get_job_profile(JobId.FIGHTER).min_mp(70) + 200,
        base_int=180,
        base_str=50,
        job="fighter",
    )
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=220,
            target_hp=25000,
            int_reset_level=155,
            int_gear=_gear(),
            job="fighter",
            mp_wash_end=120,
            resume_from=resume,
            improved_maxhp_level=3,
        )
    )
    assert result.improved_maxhp_level == 3
    assert "覆寫" in result.plan[0].notes
