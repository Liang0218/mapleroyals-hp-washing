"""Human-readable reports and CSV export."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, TextIO, Union

from hp_wash_thief.core.models import (
    CandidateResult,
    OptimizeResult,
    PolicyName,
    SimulateResult,
)


def format_optimize_report(result: OptimizeResult) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("MapleRoyals Thief HP Wash — Policy Comparison")
    lines.append("=" * 72)

    a = result.comparison.policy_a
    b = result.comparison.policy_b
    lines.append("")
    lines.append("1) Policy comparison (A vs B)")
    lines.append("-" * 72)
    lines.append(_policy_block("A  mp_wash_shortfall (PerfectSin)", a))
    lines.append(_policy_block("B  int_dump_shortfall", b))

    if result.comparison.winner and result.comparison.apr_delta is not None:
        other = (
            result.comparison.policy_b
            if result.comparison.winner.policy is PolicyName.MP_WASH_SHORTFALL
            else result.comparison.policy_a
        )
        if other is not None:
            delta = result.comparison.apr_delta
            saved = -delta
            lines.append("")
            lines.append(
                f"   ΔAPR (winner − other): {delta:+d}  "
                f"({'winner saves ' + str(saved) if saved > 0 else 'other cheaper by ' + str(-saved)} APR)"
            )
            if result.comparison.hp_delta is not None:
                lines.append(f"   ΔHP  (winner − other): {result.comparison.hp_delta:+d}")

    lines.append("")
    lines.append("2) Winner")
    lines.append("-" * 72)
    lines.append(_winner_block(result.winner))

    lines.append("")
    lines.append("3) Top candidates")
    lines.append("-" * 72)
    if not result.top_candidates:
        lines.append("  (none)")
    else:
        lines.append(
            f"  {'#':>2}  {'policy':<20}  {'INT':>4}  {'intLv':>5}  {'mpEnd':>5}  "
            f"{'thr':>3}  {'APR':>5}  {'HP':>6}  hit"
        )
        for i, c in enumerate(result.top_candidates, 1):
            lines.append(
                f"  {i:>2}  {c.policy.value:<20}  {c.target_base_int:>4}  "
                f"{c.int_reached_level:>5}  {c.mp_wash_end:>5}  {c.extra_mp_threshold:>3}  "
                f"{c.total_apr:>5}  {c.final_display_hp:>6}  "
                f"{'Y' if c.reached_target else 'N'}"
            )

    lines.append("")
    lines.append("4) Winner per-level plan (summary)")
    lines.append("-" * 72)
    if result.winner is None or not result.winner.plan:
        lines.append("  (no plan)")
    else:
        lines.extend(_plan_summary(result.winner))

    lines.append("")
    return "\n".join(lines)


def format_simulate_report(result: SimulateResult) -> str:
    cand = CandidateResult.from_simulate(result)
    lines = [
        "=" * 72,
        "MapleRoyals Thief HP Wash — Simulate",
        "=" * 72,
        _winner_block(cand),
        "",
        "Per-level plan (summary)",
        "-" * 72,
    ]
    lines.extend(_plan_summary(cand))
    lines.append("")
    return "\n".join(lines)


def write_plan_csv(plan_rows, path: Union[str, Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "level",
        "action",
        "base_int",
        "base_luk",
        "base_hp",
        "base_mp",
        "extra_mp",
        "fresh_ap_int",
        "fresh_ap_luk",
        "fresh_ap_dex",
        "fresh_ap_hp",
        "fresh_ap_mp",
        "apr_spent",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in plan_rows:
            writer.writerow(
                {
                    "level": row.level,
                    "action": row.action.value,
                    "base_int": row.base_int,
                    "base_luk": row.base_luk,
                    "base_hp": row.base_hp,
                    "base_mp": row.base_mp,
                    "extra_mp": row.extra_mp,
                    "fresh_ap_int": row.fresh_ap_int,
                    "fresh_ap_luk": row.fresh_ap_luk,
                    "fresh_ap_dex": row.fresh_ap_dex,
                    "fresh_ap_hp": row.fresh_ap_hp,
                    "fresh_ap_mp": row.fresh_ap_mp,
                    "apr_spent": row.apr_spent,
                    "notes": row.notes,
                }
            )


def print_report(text: str, file: Optional[TextIO] = None) -> None:
    print(text, end="" if text.endswith("\n") else "\n", file=file)


def _policy_block(title: str, c: Optional[CandidateResult]) -> str:
    if c is None:
        return f"  {title}: (not run)"
    hit = "yes" if c.reached_target else "NO"
    return (
        f"  {title}:\n"
        f"    target_base_int={c.target_base_int}  int_reached_level={c.int_reached_level}  "
        f"mp_wash_end={c.mp_wash_end}  threshold={c.extra_mp_threshold}\n"
        f"    total_APR={c.total_apr}  final_HP={c.final_display_hp}  hit_target={hit}\n"
        f"    APR breakdown: MP={c.apr.mp_wash_count}  M1={c.apr.method1_hp_wash_count}  "
        f"M2={c.apr.method2_hp_wash_count}  INT_reset={c.apr.int_reset_apr}"
    )


def _winner_block(c: Optional[CandidateResult]) -> str:
    if c is None:
        return "  (no winner)"
    return (
        f"  policy={c.policy.value}\n"
        f"  target_base_int={c.target_base_int}\n"
        f"  int_reached_level={c.int_reached_level}  "
        f"(early phase = until target INT, not a fixed level)\n"
        f"  mp_wash_end={c.mp_wash_end}\n"
        f"  extra_mp_threshold={c.extra_mp_threshold}  (= 12×5 for full HP5)\n"
        f"  base_int_peak={c.base_int_peak}\n"
        f"  final_base_hp={c.final_base_hp}  final_display_hp={c.final_display_hp}\n"
        f"  reached_target={c.reached_target}\n"
        f"  total_APR={c.total_apr}\n"
        f"    mp_wash={c.apr.mp_wash_count}\n"
        f"    method1_hp_wash={c.apr.method1_hp_wash_count}\n"
        f"    method2_hp_wash={c.apr.method2_hp_wash_count}\n"
        f"    int_reset_apr={c.apr.int_reset_apr}"
    )


def _plan_summary(c: CandidateResult) -> list[str]:
    lines: list[str] = []
    if not c.plan:
        return ["  (empty)"]
    lines.append(
        f"  {'lvl':>3}  {'action':<10}  {'INT':>4}  {'LUK':>4}  {'HP':>6}  {'MP':>5}  "
        f"{'xMP':>5}  {'APR':>4}  notes"
    )
    prev_action = None
    markers = {c.int_reached_level, c.mp_wash_end, c.mp_wash_end + 1}
    for row in c.plan:
        show = (
            row.level <= 30
            or row.action.value in {"RESET_INT", "M2"}
            or row.action != prev_action
            or row.level in markers
            or row.level % 10 == 0
        )
        if show:
            lines.append(
                f"  {row.level:>3}  {row.action.value:<10}  {row.base_int:>4}  {row.base_luk:>4}  "
                f"{row.base_hp:>6}  {row.base_mp:>5}  {row.extra_mp:>5}  {row.apr_spent:>4}  "
                f"{row.notes}"
            )
        prev_action = row.action
    lines.append(f"  (full plan has {len(c.plan)} rows; use --csv to export)")
    return lines
