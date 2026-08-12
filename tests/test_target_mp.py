"""Target base MP floor (optional) at max level."""

from __future__ import annotations

import pytest

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.jobs import JobId, get_job_profile
from hp_wash_thief.core.models import (
    IntGearSegment,
    OptimizeConfig,
    PolicyName,
    SimulateConfig,
)
from hp_wash_thief.ui.user_errors import format_user_error


def _gear() -> list[IntGearSegment]:
    return [IntGearSegment(from_level=1, to_level=200, int_gear=30)]


def test_target_mp_below_min_raises():
    floor = get_job_profile(JobId.THIEF).min_mp(200)
    with pytest.raises(ValueError, match="target_mp below job min_mp"):
        simulate(
            SimulateConfig(
                policy=PolicyName.INT_ONLY_PLAIN,
                target_base_int=200,
                target_hp=15000,
                int_reset_level=130,
                int_gear=_gear(),
                mp_wash_end=100,
                target_mp=floor - 1,
            )
        )


def test_target_mp_error_localized():
    floor = get_job_profile(JobId.THIEF).min_mp(200)
    exc = ValueError(f"target_mp below job min_mp at max_level (min={floor})")
    msg = format_user_error(exc)
    assert str(floor) in msg
    assert "目標 MP" in msg


def test_none_target_mp_matches_unconstrained_final_mp():
    common = dict(
        policy=PolicyName.MP_WASH_SHORTFALL,
        target_base_int=240,
        target_hp=18000,
        int_reset_level=130,
        int_gear=_gear(),
        mp_wash_end=110,
    )
    a = simulate(SimulateConfig(**common))
    b = simulate(SimulateConfig(**common, target_mp=None))
    assert a.final_base_mp == b.final_base_mp
    assert a.final_display_hp == b.final_display_hp
    assert a.apr.total_apr == b.apr.total_apr
    assert a.reached_target == b.reached_target


def test_target_mp_floor_preserved_after_method2():
    floor = get_job_profile(JobId.THIEF).min_mp(200)
    # Keep a comfortable Extra MP buffer above min.
    target_mp = floor + 400
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=280,
            target_hp=22000,
            int_reset_level=150,
            int_gear=_gear(),
            mp_wash_end=120,
            target_mp=target_mp,
        )
    )
    assert result.final_base_mp >= target_mp
    assert result.target_mp == target_mp
    if result.reached_target:
        assert result.final_display_hp >= 22000


def test_high_target_mp_can_miss_hp():
    floor = get_job_profile(JobId.THIEF).min_mp(200)
    # Extremely high MP floor leaves little Extra MP for Method2 → miss HP.
    result = simulate(
        SimulateConfig(
            policy=PolicyName.INT_ONLY_PLAIN,
            target_base_int=200,
            target_hp=50000,
            int_reset_level=130,
            int_gear=_gear(),
            mp_wash_end=100,
            target_mp=floor + 5000,
        )
    )
    assert result.final_base_mp >= floor + 5000
    assert not result.reached_target


def test_optimize_respects_target_mp():
    floor = get_job_profile(JobId.THIEF).min_mp(200)
    target_mp = floor + 200
    result = optimize(
        OptimizeConfig(
            target_hp=16000,
            int_reset_level=130,
            int_gear=_gear(),
            target_mp=target_mp,
            policies=[PolicyName.INT_ONLY_PLAIN],
            target_base_int_min=160,
            target_base_int_max=240,
            target_base_int_step=40,
            mp_wash_end_min=80,
            top_n=3,
        )
    )
    assert result.winner is not None
    if result.winner.reached_target:
        assert result.winner.final_base_mp >= target_mp
        assert result.winner.final_display_hp >= 16000
        assert result.winner.target_mp == target_mp
