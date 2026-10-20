"""Non-regression checks for the currently calculated reference solutions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.models import OptimizeConfig, PolicyName, SimulateConfig


BASELINE_PATH = Path(__file__).parent / "data" / "solution_baseline.json"


@pytest.fixture(scope="module")
def solution_baseline():
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["scenarios"]


def _assert_not_worse(result, baseline: dict[str, int | bool]) -> None:
    """Existing solutions must retain goals and must not lose HP/MP or cost more APR."""
    assert result.reached_target >= baseline["reached_target"]
    assert result.final_display_hp >= baseline["final_display_hp"]
    assert result.final_base_mp >= baseline["final_base_mp"]
    assert result.apr.total_apr <= baseline["total_apr"]


@pytest.mark.regression
def test_existing_reference_solutions_do_not_regress(example_gear, solution_baseline):
    for policy in PolicyName:
        key = f"simulate_{policy.value}"
        result = simulate(
            SimulateConfig(
                policy=policy,
                target_base_int=300,
                target_hp=25000,
                int_reset_level=155,
                int_gear=example_gear,
                mp_wash_end=130,
                int_gear_after_reset=50,
            )
        )
        _assert_not_worse(result, solution_baseline[key])

    configs = {
        "optimize_ab_27000": OptimizeConfig(
            target_hp=27000,
            int_reset_level=155,
            int_gear=example_gear,
            policies=[PolicyName.MP_WASH_SHORTFALL, PolicyName.INT_DUMP_SHORTFALL],
            target_base_int_min=280,
            target_base_int_max=360,
            target_base_int_step=40,
            mp_wash_end_min=100,
            int_gear_after_reset=50,
            top_n=3,
        ),
        "optimize_abcd_25000": OptimizeConfig(
            target_hp=25000,
            int_reset_level=150,
            int_gear=example_gear,
            target_base_int_min=240,
            target_base_int_max=360,
            target_base_int_step=40,
            mp_wash_end_min=90,
            int_gear_after_reset=50,
            top_n=5,
        ),
    }
    for key, config in configs.items():
        result = optimize(config)
        assert result.winner is not None
        _assert_not_worse(result.winner, solution_baseline[key])
