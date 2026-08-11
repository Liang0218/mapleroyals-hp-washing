"""End-to-end integration tests (API → report → CSV → CLI)."""

from __future__ import annotations

import csv
from pathlib import Path

from hp_wash_thief.cli import main
from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.models import (
    Action,
    HpMode,
    OptimizeConfig,
    PolicyName,
    SimulateConfig,
)
from hp_wash_thief.core.report import (
    format_optimize_report,
    format_simulate_report,
    write_plan_csv,
)
from tests.helpers import assert_apr_identity, assert_plan_invariants


import pytest


@pytest.mark.integration
def test_integration_simulate_all_policies_with_example_gear(example_gear):
    """Each policy can simulate through 200 with example INT gear."""
    policies = [
        PolicyName.MP_WASH_SHORTFALL,
        PolicyName.INT_DUMP_SHORTFALL,
        PolicyName.MP_WASH_HARDCORE,
        PolicyName.INT_ONLY_PLAIN,
        PolicyName.DEFERRED_MP_SHORTFALL,
    ]
    for policy in policies:
        result = simulate(
            SimulateConfig(
                policy=policy,
                target_base_int=300,
                target_hp=25000,
                int_reset_level=155,
                int_gear=example_gear,
                mp_wash_end=130,
                mp5_start_level=50,
                hp_mode=HpMode.AVG,
                int_gear_after_reset=50,
            )
        )
        assert_plan_invariants(result)
        assert result.final_display_hp > 10000
        assert result.int_reached_level >= 30
        text = format_simulate_report(result)
        assert "盜賊洗血" in text
        assert "總 APR" in text


@pytest.mark.integration
def test_integration_optimize_abe_exports_csv_and_report(example_gear, tmp_path):
    """Optimize A/B/E → Chinese report + winner CSV with action_desc."""
    result = optimize(
        OptimizeConfig(
            target_hp=27000,
            int_reset_level=155,
            int_gear=example_gear,
            policies=[
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.DEFERRED_MP_SHORTFALL,
            ],
            target_base_int_min=280,
            target_base_int_max=360,
            target_base_int_step=40,
            mp_wash_end_min=100,
            mp5_start_level_min=40,
            mp5_start_level_max=70,
            int_gear_after_reset=50,
            top_n=3,
        )
    )
    assert result.winner is not None
    assert result.winner.reached_target
    assert_apr_identity(result.winner.apr)
    assert result.comparison.policy_a is not None
    assert result.comparison.policy_b is not None
    assert result.comparison.policy_e is not None
    assert result.comparison.apr_delta is not None

    report = format_optimize_report(result)
    assert "政策比較" in report
    assert "優勝方案" in report
    assert "A：" in report or "B：" in report or "E：" in report

    csv_path = tmp_path / "winner.csv"
    write_plan_csv(result.winner.plan, csv_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    assert rows
    assert "action_desc" in rows[0]
    actions = {row["action"] for row in rows}
    assert "RESET_INT" in actions
    assert any(a.startswith("HP") or a.startswith("MP") for a in actions)


@pytest.mark.integration
def test_integration_optimize_abcde_finds_feasible_winner(example_gear):
    """Full A–E search still yields a feasible global winner."""
    result = optimize(
        OptimizeConfig(
            target_hp=25000,
            int_reset_level=150,
            int_gear=example_gear,
            target_base_int_min=240,
            target_base_int_max=360,
            target_base_int_step=40,
            mp_wash_end_min=90,
            mp5_start_level_min=40,
            mp5_start_level_max=70,
            int_gear_after_reset=50,
            top_n=5,
        )
    )
    assert set(result.by_policy) == {
        PolicyName.MP_WASH_SHORTFALL,
        PolicyName.INT_DUMP_SHORTFALL,
        PolicyName.MP_WASH_HARDCORE,
        PolicyName.INT_ONLY_PLAIN,
        PolicyName.DEFERRED_MP_SHORTFALL,
    }
    assert result.winner is not None
    assert result.winner.reached_target
    assert result.comparison.winner is result.winner
    assert len(result.top_candidates) >= 1
    assert all(c.reached_target for c in result.top_candidates)


@pytest.mark.integration
def test_integration_cli_optimize_and_simulate(example_gear_path: Path, tmp_path: Path):
    """CLI optimize (E) and simulate (E) both write CSV."""
    opt_csv = tmp_path / "opt.csv"
    rc = main(
        [
            "optimize",
            "--target-hp",
            "25000",
            "--int-reset-level",
            "155",
            "--int-gear-file",
            str(example_gear_path),
            "--policies",
            "deferred_mp_shortfall",
            "--csv",
            str(opt_csv),
        ]
    )
    assert rc == 0
    assert opt_csv.is_file()
    assert "RESET_INT" in opt_csv.read_text(encoding="utf-8-sig")

    sim_csv = tmp_path / "sim.csv"
    rc = main(
        [
            "simulate",
            "--policy",
            "deferred_mp_shortfall",
            "--target-base-int",
            "320",
            "--target-hp",
            "25000",
            "--int-reset-level",
            "155",
            "--int-gear-file",
            str(example_gear_path),
            "--mp-wash-end",
            "120",
            "--mp5-start-level",
            "55",
            "--csv",
            str(sim_csv),
        ]
    )
    assert rc == 0
    assert sim_csv.is_file()
    header = sim_csv.read_text(encoding="utf-8-sig").splitlines()[0]
    assert "action_desc" in header


@pytest.mark.integration
def test_integration_policy_e_plan_transitions(example_gear):
    """Policy E plan: INT dump before mp5_start, MP5 allowed after, then reset."""
    result = simulate(
        SimulateConfig(
            policy=PolicyName.DEFERRED_MP_SHORTFALL,
            target_base_int=300,
            target_hp=24000,
            int_reset_level=150,
            int_gear=example_gear,
            mp_wash_end=125,
            mp5_start_level=60,
            int_gear_after_reset=50,
        )
    )
    assert_plan_invariants(result)
    before = [r for r in result.plan if 31 <= r.level < 60]
    after = [
        r
        for r in result.plan
        if 60 <= r.level <= result.int_reached_level and result.int_reached_level
    ]
    assert before
    assert all(r.action is not Action.MP5 for r in before)
    # After start, shortfall may be MP5 (or HP5 if Extra MP enough).
    if after:
        assert any(r.action in {Action.MP5, Action.HP5, Action.INT5} for r in after)
