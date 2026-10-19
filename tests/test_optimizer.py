"""Optimizer smoke tests (narrow search grid)."""

from __future__ import annotations

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.gear import parse_int_gear
from hp_wash_thief.core.models import Action, AprBreakdown, CandidateResult, IntGearSegment, OptimizeConfig, PolicyName, ResumeFrom, SimulateConfig
from hp_wash_thief.core.optimizer import _candidate_sort_key, _mp_wash_end_candidates
from hp_wash_thief.core.report import format_optimize_summary_text


GEAR = parse_int_gear(
    [
        {"from_level": 1, "to_level": 200, "int_gear": 100},
    ]
)


def test_optimizer_default_int_search_includes_no_extra_int_and_high_values():
    config = OptimizeConfig(target_hp=22000, int_reset_level=140, int_gear=GEAR)

    assert config.target_base_int_min == 4
    assert config.target_base_int_max == 999


def test_optimize_abd_policies_narrow():
    result = optimize(
        OptimizeConfig(
            target_hp=22000,
            int_reset_level=140,
            int_gear=GEAR,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.INT_ONLY_PLAIN,
            ],
            target_base_int_min=200,
            target_base_int_max=280,
            target_base_int_step=40,
            mp_wash_end_min=70,
            extra_mp_threshold=60,
            top_n=3,
        )
    )
    assert result.winner is not None
    assert PolicyName.MP_WASH_SHORTFALL in result.by_policy
    assert PolicyName.INT_DUMP_SHORTFALL in result.by_policy
    assert PolicyName.INT_ONLY_PLAIN in result.by_policy
    assert result.comparison.winner is not None
    assert result.comparison.policy_c is None
    assert result.comparison.policy_d is not None
    assert result.winner.apr.total_apr == result.winner.total_apr
    assert result.winner.extra_mp_threshold == 60
    assert result.winner.int_reached_level > 0


def test_optimize_all_policies_abcd():
    result = optimize(
        OptimizeConfig(
            target_hp=22000,
            int_reset_level=140,
            int_gear=GEAR,
            target_base_int_min=200,
            target_base_int_max=280,
            target_base_int_step=40,
            mp_wash_end_min=70,
            top_n=3,
        )
    )
    assert PolicyName.MP_WASH_HARDCORE in result.by_policy
    assert PolicyName.INT_ONLY_PLAIN in result.by_policy
    assert result.comparison.policy_c is not None
    assert result.comparison.policy_d is not None
    assert result.comparison.winner is not None
    bests = [
        c
        for c in (
            result.comparison.policy_a,
            result.comparison.policy_b,
            result.comparison.policy_c,
            result.comparison.policy_d,
        )
        if c is not None
    ]
    assert result.comparison.winner in bests
    assert result.comparison.apr_delta is not None


def test_mp_wash_end_grid_includes_skip_sentinel():
    cfg = OptimizeConfig(
        target_hp=10000,
        int_reset_level=80,
        int_gear=GEAR,
    )
    assert cfg.mp_wash_end_min == 31
    values = _mp_wash_end_candidates(cfg, step=10)
    assert values[0] == 31


def test_hp_reached_but_mp_missed_prefers_highest_mp_before_apr():
    common = dict(
        policy=PolicyName.INT_ONLY_PLAIN,
        target_base_int=200,
        int_reached_level=50,
        mp_wash_end=100,
        extra_mp_threshold=60,
        int_gear_after_reset=50,
        final_base_hp=20000,
        final_display_hp=20000,
        base_int_peak=200,
        reached_target=False,
        target_hp=20000,
        target_mp=8000,
    )
    lower_mp = CandidateResult(final_base_mp=7000, apr=AprBreakdown(method2_hp_wash_count=10), **common)
    higher_mp = CandidateResult(final_base_mp=7500, apr=AprBreakdown(method2_hp_wash_count=20), **common)

    assert sorted([lower_mp, higher_mp], key=_candidate_sort_key)[0] is higher_mp


def test_infeasible_optimizer_prioritizes_hp_then_mp_then_apr():
    common = dict(
        policy=PolicyName.INT_ONLY_PLAIN,
        target_base_int=20,
        int_reached_level=50,
        mp_wash_end=100,
        extra_mp_threshold=60,
        int_gear_after_reset=50,
        final_base_hp=10000,
        final_display_hp=10000,
        base_int_peak=20,
        reached_target=False,
        target_hp=20000,
        target_mp=10000,
    )
    mp_closer_but_hp_farther = CandidateResult(
        final_base_mp=10000,
        apr=AprBreakdown(),
        **{**common, "final_base_hp": 9000, "final_display_hp": 9000},
    )
    hp_closer = CandidateResult(final_base_mp=4000, apr=AprBreakdown(method2_hp_wash_count=100), **common)
    same_goals_lower_apr = CandidateResult(final_base_mp=4000, apr=AprBreakdown(method2_hp_wash_count=50), **common)

    assert sorted([mp_closer_but_hp_farther, hp_closer], key=_candidate_sort_key)[0] is hp_closer
    assert sorted([hp_closer, same_goals_lower_apr], key=_candidate_sort_key)[0] is same_goals_lower_apr


def test_optimizer_can_trade_mp_below_target_to_reach_hp():
    result = optimize(
        OptimizeConfig(
            target_hp=27000,
            target_mp=30000,
            int_reset_level=170,
            int_gear=GEAR,
            job="bowman",
            max_level=200,
            policies=[PolicyName.INT_ONLY_PLAIN],
            target_base_int_min=400,
            target_base_int_max=520,
            target_base_int_step=20,
            mp_wash_end_min=150,
        )
    )

    assert result.winner is not None
    assert result.winner.final_display_hp >= 27000
    assert result.winner.final_base_mp < 30000
    assert result.winner.reached_target is False


def test_infeasible_bowman_searches_recurring_early_mp5_levels():
    config = dict(
        target_hp=27000,
        target_mp=30000,
        int_reset_level=170,
        int_gear=GEAR,
        job="bowman",
        max_level=200,
        target_base_int_min=480,
        target_base_int_max=480,
        target_base_int_step=20,
        mp_wash_end_min=170,
    )
    result = optimize(OptimizeConfig(**config))
    regular = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=480,
            target_hp=27000,
            int_reset_level=170,
            int_gear=GEAR,
            job="bowman",
            max_level=200,
            mp_wash_end=170,
        )
    )

    assert result.winner is not None
    assert result.winner.early_mp_wash_level is not None
    assert result.winner.final_display_hp == regular.final_display_hp
    assert result.winner.final_base_mp > regular.final_base_mp
    assert result.winner.total_apr > regular.apr.total_apr
    early_rows = [
        row for row in result.winner.plan
        if result.winner.early_mp_wash_level <= row.level < result.winner.int_reached_level
    ]
    assert len(early_rows) > 1
    assert all(row.action is Action.MP5 for row in early_rows)
    early_row = early_rows[0]
    assert early_row.fresh_ap_mp >= 5
    assert early_row.apr_spent == early_row.fresh_ap_mp
    assert f"INT {early_row.fresh_ap_mp} DEX 0" in early_row.notes


def test_early_mp5_search_pairs_higher_int_targets_with_later_starts():
    result = optimize(
        OptimizeConfig(
            target_hp=30000,
            target_mp=29000,
            int_reset_level=170,
            max_level=200,
            job="bowman",
            policies=[PolicyName.INT_ONLY_PLAIN],
            int_gear=[
                IntGearSegment(108, 119, 170),
                IntGearSegment(120, 169, 190),
            ],
            int_gear_after_reset=170,
            mp_wash_end_min=170,
            target_base_int_min=524,
            target_base_int_max=634,
            target_base_int_step=10,
            resume_from=ResumeFrom(
                level=108,
                base_hp=3444,
                base_mp=18943,
                base_int=524,
                base_dex=100,
            ),
        )
    )

    assert result.winner is not None
    assert result.winner.reached_target
    assert result.winner.target_base_int > 524
    assert result.winner.early_mp_wash_level is not None
    assert result.winner.early_mp_wash_level > 108
    assert result.winner.final_base_mp >= 29000
    assert result.winner.final_display_hp >= 30000


def test_optimize_skips_forced_mp_wash_to_50_when_unneeded():
    """Easy HP must not keep MP-washing through the old min 50 after INT lands."""
    result = optimize(
        OptimizeConfig(
            target_hp=8000,
            int_reset_level=120,
            int_gear=GEAR,
            policies=[PolicyName.INT_ONLY_PLAIN],
            target_base_int_min=140,
            target_base_int_max=180,
            target_base_int_step=40,
            top_n=3,
        )
    )
    assert result.winner is not None
    assert result.winner.reached_target
    assert result.winner.mp_wash_end < 50
    leftover_mp = [
        r
        for r in result.winner.plan
        if 32 <= r.level <= 50 and r.fresh_ap_mp > 0
    ]
    assert leftover_mp == []
    text = format_optimize_summary_text(result)
    if result.winner.mp_wash_end < result.winner.int_reached_level:
        assert "達標 INT 後不再 MP wash" in text

    forced = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=result.winner.target_base_int,
            target_hp=8000,
            int_reset_level=120,
            int_gear=GEAR,
            mp_wash_end=50,
        )
    )
    assert forced.apr.mp_wash_count > result.winner.apr.mp_wash_count
