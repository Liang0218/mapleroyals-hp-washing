"""Terminal CLI for Phase 1."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.formulas import EXTRA_MP_THRESHOLD_DEFAULT
from hp_wash_thief.core.gear import load_int_gear
from hp_wash_thief.core.models import HpMode, OptimizeConfig, PolicyName, SimulateConfig
from hp_wash_thief.core.report import (
    format_optimize_report,
    format_simulate_report,
    print_report,
    write_plan_csv,
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hp_wash_thief",
        description="MapleRoyals Thief HP Wash APR Optimizer (Phase 1 CLI)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    opt = sub.add_parser("optimize", help="Search policies for lowest APR")
    _add_shared_args(opt)
    opt.add_argument(
        "--policies",
        default="all",
        choices=[
            "all",
            "abd",
            "mp_wash_shortfall",
            "int_dump_shortfall",
            "mp_wash_hardcore",
            "int_only_plain",
        ],
        help="Which policies to search: all=ABCD (default), abd=ABD only",
    )
    opt.add_argument("--csv", dest="csv_path", default=None, help="Write winner plan CSV")
    opt.add_argument("--top", type=int, default=5, help="Top-N candidates to retain")

    sim = sub.add_parser("simulate", help="Simulate one parameterized plan")
    _add_shared_args(sim)
    sim.add_argument(
        "--policy",
        required=True,
        choices=[
            "mp_wash_shortfall",
            "int_dump_shortfall",
            "mp_wash_hardcore",
            "int_only_plain",
        ],
    )
    sim.add_argument("--target-base-int", type=int, required=True)
    sim.add_argument("--mp-wash-end", type=int, default=135)
    sim.add_argument("--csv", dest="csv_path", default=None, help="Write plan CSV")
    sim.add_argument(
        "--no-method2",
        action="store_true",
        help="Disable automatic Method 2 top-up",
    )

    args = parser.parse_args(argv)
    if args.command == "optimize":
        return _cmd_optimize(args)
    if args.command == "simulate":
        return _cmd_simulate(args)
    parser.error(f"unknown command: {args.command}")
    return 2


def _add_shared_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--target-hp", type=int, required=True, help="Target base/display HP at 200")
    p.add_argument("--int-reset-level", type=int, required=True, help="Level to reset INT→LUK")
    p.add_argument("--int-gear-file", required=True, help="Path to INT gear JSON")
    p.add_argument("--quest-equip-hp", type=int, default=0, help="Flat HP from quests/equips")
    p.add_argument(
        "--hp-mode",
        default="avg",
        choices=["avg", "min", "max"],
        help="Use avg/min/max of HP/MP gain ranges",
    )
    p.add_argument(
        "--mw-percent",
        type=float,
        default=0.10,
        help="Maple Warrior as fraction of base INT for level-up MP (default: 0.10)",
    )
    p.add_argument(
        "--mw-from-level",
        type=int,
        default=10,
        help="First level MW is active (default: 10)",
    )
    p.add_argument(
        "--extra-mp-threshold",
        type=int,
        default=EXTRA_MP_THRESHOLD_DEFAULT,
        help=f"Extra MP needed for HP wash×5 (default: {EXTRA_MP_THRESHOLD_DEFAULT} = 12×5)",
    )
    p.add_argument(
        "--int-gear-after-reset",
        type=int,
        default=50,
        help="Equipment INT from int-reset level onward (default: 50)",
    )


def _parse_policies(value: str) -> list[PolicyName]:
    if value == "all":
        return [
            PolicyName.MP_WASH_SHORTFALL,
            PolicyName.INT_DUMP_SHORTFALL,
            PolicyName.MP_WASH_HARDCORE,
            PolicyName.INT_ONLY_PLAIN,
        ]
    if value == "abd":
        return [
            PolicyName.MP_WASH_SHORTFALL,
            PolicyName.INT_DUMP_SHORTFALL,
            PolicyName.INT_ONLY_PLAIN,
        ]
    return [PolicyName(value)]


def _cmd_optimize(args: argparse.Namespace) -> int:
    gear = load_int_gear(args.int_gear_file)
    config = OptimizeConfig(
        target_hp=args.target_hp,
        int_reset_level=args.int_reset_level,
        int_gear=gear,
        policies=_parse_policies(args.policies),
        quest_equip_hp=args.quest_equip_hp,
        hp_mode=HpMode(args.hp_mode),
        mw_percent=args.mw_percent,
        mw_from_level=args.mw_from_level,
        extra_mp_threshold=args.extra_mp_threshold,
        int_gear_after_reset=args.int_gear_after_reset,
        top_n=args.top,
    )
    result = optimize(config)
    print_report(format_optimize_report(result))
    if args.csv_path:
        if result.winner is None:
            print("沒有可匯出的優勝計畫。", file=sys.stderr)
            return 1
        write_plan_csv(result.winner.plan, args.csv_path)
        print(f"已寫入優勝計畫 CSV：{args.csv_path}")
    return 0 if result.winner and result.winner.reached_target else 1


def _cmd_simulate(args: argparse.Namespace) -> int:
    gear = load_int_gear(args.int_gear_file)
    config = SimulateConfig(
        policy=PolicyName(args.policy),
        target_base_int=args.target_base_int,
        target_hp=args.target_hp,
        int_reset_level=args.int_reset_level,
        int_gear=gear,
        mp_wash_end=args.mp_wash_end,
        extra_mp_threshold=args.extra_mp_threshold,
        quest_equip_hp=args.quest_equip_hp,
        hp_mode=HpMode(args.hp_mode),
        auto_method2=not args.no_method2,
        mw_percent=args.mw_percent,
        mw_from_level=args.mw_from_level,
        int_gear_after_reset=args.int_gear_after_reset,
    )
    result = simulate(config)
    print_report(format_simulate_report(result))
    if args.csv_path:
        write_plan_csv(result.plan, args.csv_path)
        print(f"已寫入計畫 CSV：{args.csv_path}")
    return 0 if result.reached_target else 1


if __name__ == "__main__":
    raise SystemExit(main())
