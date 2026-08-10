"""Policy C (hardcore A) tests."""

from __future__ import annotations

from hp_wash_thief.core.formulas import MP_REMOVED_PER_APR, min_mp, method1_washes_affordable
from hp_wash_thief.core.models import Action, HpMode
from hp_wash_thief.core.policy import mp_wash_hardcore


def test_method1_washes_affordable():
    assert method1_washes_affordable(12, 5) == 1
    assert method1_washes_affordable(11, 5) == 0
    assert method1_washes_affordable(60, 5) == 5
    assert method1_washes_affordable(36, 5) == 3
    assert method1_washes_affordable(120, 10) == 10


def test_hardcore_always_uses_greedy_action():
    assert mp_wash_hardcore.choose_level_action(15) is Action.HARDCORE_GREEDY
    assert mp_wash_hardcore.choose_level_action(30) is Action.HARDCORE_GREEDY


def test_greedy_hp1_when_twelve_extra_mp():
    level = 15
    plan = mp_wash_hardcore.plan_greedy_wash(
        base_int=200,
        base_mp=float(min_mp(level) + 12),
        level=level,
        fresh_ap=5,
        allow_mp=False,
        hp_mode=HpMode.AVG,
    )
    assert plan.hp_washes == 1
    assert plan.mp_washes == 0
    assert plan.int_dump == 4
    assert [s.kind for s in plan.steps] == ["HP", "INT", "INT", "INT", "INT"]


def test_greedy_no_mp_before_30():
    level = 25
    plan = mp_wash_hardcore.plan_greedy_wash(
        base_int=50,
        base_mp=float(min_mp(level) + 5),
        level=level,
        fresh_ap=5,
        allow_mp=False,
        hp_mode=HpMode.AVG,
    )
    assert plan.mp_washes == 0
    assert plan.hp_washes == 0
    assert plan.int_dump == 5


def test_greedy_interleaved_mp_then_hp_at_30():
    """Extra MP = 11 → MP1 can push over 12, next AP slot → HP1."""
    level = 30
    base_int = 200
    plan = mp_wash_hardcore.plan_greedy_wash(
        base_int=base_int,
        base_mp=float(min_mp(level) + 11),
        level=level,
        fresh_ap=5,
        allow_mp=True,
        hp_mode=HpMode.AVG,
    )
    kinds = [s.kind for s in plan.steps]
    assert kinds[0] == "MP"
    assert "HP" in kinds
    assert kinds.index("MP") < kinds.index("HP")
    assert plan.mp_washes >= 1
    assert plan.hp_washes >= 1


def test_greedy_int_dump_when_no_wash_possible():
    level = 30
    plan = mp_wash_hardcore.plan_greedy_wash(
        base_int=4,
        base_mp=float(min_mp(level)),
        level=level,
        fresh_ap=5,
        allow_mp=True,
        hp_mode=HpMode.AVG,
    )
    assert plan.hp_washes == 0
    assert plan.mp_washes == 0
    assert plan.int_dump == 5


def test_hardcore_threshold_is_one_apr():
    assert MP_REMOVED_PER_APR == 12
    level = 25
    assert (
        mp_wash_hardcore.plan_greedy_wash(
            base_int=50,
            base_mp=float(min_mp(level) + 11.9),
            level=level,
            fresh_ap=5,
            allow_mp=False,
            hp_mode=HpMode.AVG,
        ).hp_washes
        == 0
    )
    assert (
        mp_wash_hardcore.plan_greedy_wash(
            base_int=50,
            base_mp=float(min_mp(level) + 12.0),
            level=level,
            fresh_ap=5,
            allow_mp=False,
            hp_mode=HpMode.AVG,
        ).hp_washes
        == 1
    )
