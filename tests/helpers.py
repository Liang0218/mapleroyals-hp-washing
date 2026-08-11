"""Shared assertion helpers (safe to import from test modules)."""

from __future__ import annotations

from hp_wash_thief.core.models import AprBreakdown, SimulateResult


def assert_apr_identity(apr: AprBreakdown) -> None:
    assert apr.total_apr == (
        apr.mp_wash_count
        + apr.method1_hp_wash_count
        + apr.method2_hp_wash_count
        + apr.int_reset_apr
    )
    assert apr.mp_wash_count >= 0
    assert apr.method1_hp_wash_count >= 0
    assert apr.method2_hp_wash_count >= 0
    assert apr.int_reset_apr >= 0


def assert_plan_invariants(result: SimulateResult) -> None:
    assert result.plan, "plan must not be empty"
    assert result.plan[0].level == 1
    assert result.base_int_peak >= 4
    assert_apr_identity(result.apr)
    if result.apr.int_reset_apr:
        assert result.apr.int_reset_apr == result.base_int_peak - 4
        reset_rows = [r for r in result.plan if r.action.value == "RESET_INT"]
        assert reset_rows, "INT reset APR spent but no RESET_INT row"
        idx = result.plan.index(reset_rows[0])
        assert all(r.base_int == 4 for r in result.plan[idx:])
