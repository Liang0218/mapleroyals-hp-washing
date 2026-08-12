"""Terminal CLI for MapleRoyals multi-job HP wash optimizer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.gear import load_int_gear
from hp_wash_thief.core.jobs import JobId, get_job_profile
from hp_wash_thief.core.models import HpMode, OptimizeConfig, PolicyName, ResumeFrom, SimulateConfig
from hp_wash_thief.core.report import (
    format_optimize_report,
    format_simulate_report,
    print_report,
    write_plan_csv,
)

_JOB_CHOICES = [j.value for j in JobId]


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hp_wash_thief",
        description="MapleRoyals HP Wash APR Optimizer (multi-job)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    opt = sub.add_parser("optimize", help="Search policies for lowest APR")
    _add_shared_args(opt)
    _add_resume_args(opt)
    opt.add_argument(
        "--policies",
        default="auto",
        choices=[
            "auto",
            "all",
            "abd",
            "mp_wash_shortfall",
            "int_dump_shortfall",
            "mp_wash_hardcore",
            "int_only_plain",
        ],
        help="Policies: auto=job default (Thief ABCD / others D only)",
    )
    opt.add_argument("--csv", dest="csv_path", default=None, help="Write winner plan CSV")
    opt.add_argument("--top", type=int, default=5, help="Top-N candidates to retain")

    sim = sub.add_parser("simulate", help="Simulate one parameterized plan")
    _add_shared_args(sim)
    _add_resume_args(sim)
    sim.add_argument(
        "--policy",
        default=None,
        choices=[
            "mp_wash_shortfall",
            "int_dump_shortfall",
            "mp_wash_hardcore",
            "int_only_plain",
        ],
        help="Wash policy (default: job default; non-Thief → int_only_plain)",
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
    p.add_argument(
        "--job",
        default="thief",
        choices=_JOB_CHOICES,
        help="Job class (default: thief)",
    )
    p.add_argument("--target-hp", type=int, required=True, help="Target base/display HP at 200")
    p.add_argument("--int-reset-level", type=int, required=True, help="Level to reset INT→primary")
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
        default=None,
        help="Extra MP for HP wash×5 (default: job mp_removed×5)",
    )
    p.add_argument(
        "--int-gear-after-reset",
        type=int,
        default=50,
        help="Equipment INT from int-reset level onward (default: 50)",
    )
    p.add_argument(
        "--improved-maxhp-level",
        type=int,
        default=None,
        help="Override Improve MaxHP skill level 0–10 (Warrior/Brawler; default: auto SP)",
    )
    p.add_argument(
        "--target-mp",
        type=int,
        default=None,
        help="Min base MP at max level (default: wash Extra MP to near job min_mp)",
    )


def _add_resume_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group(
        "mid-game resume",
        "Provide current character stats to continue from mid-game "
        "(APR reported is remaining from this point).",
    )
    g.add_argument(
        "--from-level",
        type=int,
        default=None,
        help="Current level (already leveled into; fresh AP not yet spent)",
    )
    g.add_argument("--base-hp", type=float, default=None, help="Current base HP")
    g.add_argument("--base-mp", type=float, default=None, help="Current base MP")
    g.add_argument(
        "--extra-mp",
        type=float,
        default=None,
        help="Current Extra MP (alternative to --base-mp; base_mp = min_mp + extra_mp)",
    )
    g.add_argument("--base-int", type=int, default=None, help="Current base INT")
    g.add_argument("--base-luk", type=int, default=4, help="Current base LUK (default: 4)")
    g.add_argument("--base-dex", type=int, default=25, help="Current base DEX (default: 25)")
    g.add_argument("--base-str", type=int, default=4, help="Current base STR (default: 4)")
    g.add_argument(
        "--fresh-ap",
        type=int,
        default=None,
        help="Unspent fresh AP this level (default: 5; use 10 at 70/120 if job AP unspent)",
    )
    g.add_argument(
        "--int-reset-done",
        action="store_true",
        help="INT has already been reset to 4",
    )
    g.add_argument(
        "--base-int-peak",
        type=int,
        default=None,
        help="Historical peak base INT (default: current --base-int)",
    )


def _parse_resume(args: argparse.Namespace) -> Optional[ResumeFrom]:
    if args.from_level is None:
        return None
    if args.base_hp is None or args.base_int is None:
        raise SystemExit("mid-game resume requires --from-level, --base-hp, and --base-int")
    if args.base_mp is None and args.extra_mp is None:
        raise SystemExit("mid-game resume requires --base-mp or --extra-mp")
    return ResumeFrom.from_stats(
        level=args.from_level,
        base_hp=args.base_hp,
        base_mp=args.base_mp,
        extra_mp=args.extra_mp,
        base_int=args.base_int,
        base_luk=args.base_luk,
        base_dex=args.base_dex,
        base_str=getattr(args, "base_str", 4),
        fresh_ap=args.fresh_ap,
        int_reset_done=args.int_reset_done,
        base_int_peak=args.base_int_peak,
        job=args.job,
    )


def _parse_policies(value: str, job: str) -> list[PolicyName]:
    if value == "auto":
        return list(get_job_profile(job).policies)
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
        job=args.job,
        policies=_parse_policies(args.policies, args.job),
        quest_equip_hp=args.quest_equip_hp,
        hp_mode=HpMode(args.hp_mode),
        mw_percent=args.mw_percent,
        mw_from_level=args.mw_from_level,
        extra_mp_threshold=args.extra_mp_threshold,
        int_gear_after_reset=args.int_gear_after_reset,
        top_n=args.top,
        resume_from=_parse_resume(args),
        improved_maxhp_level=args.improved_maxhp_level,
        target_mp=args.target_mp,
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
    profile = get_job_profile(args.job)
    policy = (
        PolicyName(args.policy)
        if args.policy
        else profile.policies[0]
    )
    config = SimulateConfig(
        policy=policy,
        target_base_int=args.target_base_int,
        target_hp=args.target_hp,
        int_reset_level=args.int_reset_level,
        int_gear=gear,
        job=args.job,
        mp_wash_end=args.mp_wash_end,
        extra_mp_threshold=args.extra_mp_threshold,
        quest_equip_hp=args.quest_equip_hp,
        hp_mode=HpMode(args.hp_mode),
        auto_method2=not args.no_method2,
        mw_percent=args.mw_percent,
        mw_from_level=args.mw_from_level,
        int_gear_after_reset=args.int_gear_after_reset,
        resume_from=_parse_resume(args),
        improved_maxhp_level=args.improved_maxhp_level,
        target_mp=args.target_mp,
    )
    result = simulate(config)
    print_report(format_simulate_report(result))
    if args.csv_path:
        write_plan_csv(result.plan, args.csv_path)
        print(f"已寫入計畫 CSV：{args.csv_path}")
    return 0 if result.reached_target else 1


if __name__ == "__main__":
    raise SystemExit(main())
