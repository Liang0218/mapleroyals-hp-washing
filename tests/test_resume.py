"""Mid-game resume (continue from current level/stats)."""

from __future__ import annotations

import pytest

from hp_wash_thief.cli import main
from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.formulas import extra_mp, min_mp
from hp_wash_thief.core.models import (
    Action,
    HpMode,
    OptimizeConfig,
    PolicyName,
    ResumeFrom,
    SimulateConfig,
)
from hp_wash_thief.core.report import format_simulate_report
from tests.helpers import assert_apr_identity, assert_plan_invariants


def test_resume_from_extra_mp_derives_base_mp():
    resume = ResumeFrom.from_stats(
        level=80, base_hp=12000, extra_mp=500, base_int=280, base_luk=40
    )
    assert resume.base_mp == pytest.approx(min_mp(80) + 500)


def test_resume_simulate_starts_at_snapshot_level(example_gear):
    resume = ResumeFrom.from_stats(
        level=90,
        base_hp=14000,
        extra_mp=800,
        base_int=320,
        base_luk=60,
        fresh_ap=5,
    )
    result = simulate(
        SimulateConfig(
            policy=PolicyName.MP_WASH_SHORTFALL,
            target_base_int=320,
            target_hp=22000,
            int_reset_level=155,
            int_gear=example_gear,
            mp_wash_end=120,
            hp_mode=HpMode.AVG,
            int_gear_after_reset=50,
            resume_from=resume,
        )
    )
    assert_plan_invariants(result)
    assert result.resume_from is resume
    assert result.plan[0].action is Action.RESUME
    assert all(r.level >= 90 for r in result.plan)
    assert result.apr.int_reset_apr == result.base_int_peak - 4
    assert result.base_int_peak >= 320
    assert "中途接續" in format_simulate_report(result)
    assert "剩餘 APR" in format_simulate_report(result)


def test_resume_int_already_reset_no_second_reset_apr(example_gear):
    resume = ResumeFrom.from_stats(
        level=160,
        base_hp=20000,
        extra_mp=1200,
        base_int=4,
        base_luk=400,
        int_reset_done=True,
        base_int_peak=320,
    )
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_DUMP_SHORTFALL,
            target_base_int=320,
            target_hp=24000,
            int_reset_level=155,
            int_gear=example_gear,
            mp_wash_end=135,
            int_gear_after_reset=50,
            resume_from=resume,
        )
    )
    assert result.apr.int_reset_apr == 0
    assert not any(r.action is Action.RESET_INT for r in result.plan)
    assert result.reached_target or result.final_display_hp >= 20000


def test_resume_rejects_reset_done_with_high_int(example_gear):
    resume = ResumeFrom.from_stats(
        level=160,
        base_hp=20000,
        extra_mp=100,
        base_int=50,
        int_reset_done=True,
    )
    with pytest.raises(ValueError, match="int_reset_done"):
        simulate(
            SimulateConfig(
                policy=PolicyName.MP_WASH_SHORTFALL,
                target_base_int=320,
                target_hp=27000,
                int_reset_level=155,
                int_gear=example_gear,
                mp_wash_end=120,
                resume_from=resume,
            )
        )


def test_optimize_resume_finds_feasible_winner(example_gear):
    resume = ResumeFrom.from_stats(
        level=70,
        base_hp=9000,
        extra_mp=400,
        base_int=200,
        base_luk=30,
        fresh_ap=10,  # just job advanced
    )
    result = optimize(
        OptimizeConfig(
            target_hp=22000,
            int_reset_level=150,
            int_gear=example_gear,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
            ],
            target_base_int_min=200,
            target_base_int_max=360,
            target_base_int_step=40,
            mp_wash_end_min=100,
            int_gear_after_reset=50,
            top_n=3,
            resume_from=resume,
        )
    )
    assert result.resume_from is resume
    assert result.winner is not None
    assert result.winner.reached_target
    assert result.winner.target_base_int >= 200
    assert_apr_identity(result.winner.apr)
    assert result.winner.plan[0].action is Action.RESUME


def test_cli_simulate_resume(example_gear_path, tmp_path):
    csv_path = tmp_path / "resume.csv"
    rc = main(
        [
            "simulate",
            "--policy",
            "mp_wash_shortfall",
            "--target-base-int",
            "320",
            "--target-hp",
            "22000",
            "--int-reset-level",
            "155",
            "--int-gear-file",
            str(example_gear_path),
            "--mp-wash-end",
            "120",
            "--from-level",
            "85",
            "--base-hp",
            "13000",
            "--extra-mp",
            "700",
            "--base-int",
            "300",
            "--base-luk",
            "50",
            "--csv",
            str(csv_path),
        ]
    )
    assert rc == 0
    text = csv_path.read_text(encoding="utf-8-sig")
    assert "RESUME" in text
    assert "中途接續" in text or "action_desc" in text


def test_resume_extra_mp_matches_formula(example_gear):
    emp = 640.0
    level = 100
    resume = ResumeFrom.from_stats(
        level=level, base_hp=15000, extra_mp=emp, base_int=320
    )
    assert extra_mp(resume.base_mp, level) == pytest.approx(emp)
