"""Human-readable reports and CSV export (Traditional Chinese)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional, TextIO, Union

from hp_wash_thief.core.models import (
    Action,
    CandidateResult,
    OptimizeResult,
    PolicyName,
    SimulateResult,
)


def action_description(action: Action) -> str:
    """Traditional Chinese one-line explanation for plan CSV / report / UI."""
    descriptions: dict[Action, str] = {
        Action.NONE: "（無）",
        Action.BUILD: "升等 AP 建 DEX／堆 INT（30 等前，0 wash APR）",
        Action.HP1: "Method 1 洗血 ×1（-12 Extra MP，+20~24 HP，1 APR）",
        Action.HP2: "Method 1 洗血 ×2（-24 Extra MP，2 APR）",
        Action.HP3: "Method 1 洗血 ×3（-36 Extra MP，3 APR）",
        Action.HP4: "Method 1 洗血 ×4（-48 Extra MP，4 APR）",
        Action.HP5: "Method 1 洗血 ×5（需 Extra MP ≥60，5 APR）",
        Action.MP1: "MP wash ×1（1 AP → MP，成功 -12 Extra MP，1 APR）",
        Action.MP2: "MP wash ×2（2 APR）",
        Action.MP3: "MP wash ×3（3 APR）",
        Action.MP4: "MP wash ×4（4 APR）",
        Action.MP5: "MP wash ×5（5 APR）",
        Action.HARDCORE_GREEDY: "硬核 C：逐 AP 貪婪（≥12 → HP1；30+ 不足 → MP1；剩餘 → INT）",
        Action.INT5: "5 點 AP 全點 INT（本等 0 wash APR）",
        Action.LUK5: "5 點 AP 全點 LUK（本等 0 wash APR）",
        Action.M2: "Method 2 補洗（APR MP → HP，-12 MP / +16~20 HP）",
        Action.RESET_INT: "INT 洗回 4，轉 LUK（消耗 INT 洗回 APR）",
    }
    return descriptions.get(action, action.value)


def extra_mp_threshold_display(policy: PolicyName, threshold: int) -> str:
    if policy is PolicyName.MP_WASH_HARDCORE:
        return "Extra MP 門檻=12（每次 HP wash；逐 AP 貪婪 HP1/MP1，非 60）"
    return f"Extra MP 門檻={threshold}（= 12×5，完整 HP wash×5）"


def extra_mp_threshold_short(policy: PolicyName, threshold: int) -> str:
    if policy is PolicyName.MP_WASH_HARDCORE:
        return "12/次"
    return str(threshold)


def format_action_legend() -> str:
    """Full action glossary for the UI help tab."""
    lines = [
        "【政策說明】",
        "",
        policy_label(PolicyName.MP_WASH_SHORTFALL),
        "  Extra MP ≥60 → HP wash×5；不足 → MP wash×5。31 等起進入 early 階段。",
        "",
        policy_label(PolicyName.INT_DUMP_SHORTFALL),
        "  Extra MP ≥60 → HP wash×5；不足 → 5 AP 全點 INT（0 wash APR）。",
        "",
        policy_label(PolicyName.MP_WASH_HARDCORE),
        "  10 等起至達標 INT：每點 AP 依序檢查 Extra MP ≥12 → HP1；",
        "  30 等起若仍不足 → MP1；洗不動 → 剩餘 AP 點 INT/LUK。",
        "  （門檻是每次 12，不是 A/B 的 60。）",
        "",
        "【動作代碼】",
        "",
    ]
    for action in Action:
        if action is Action.NONE:
            continue
        lines.append(f"  {action.value:<16}  {action_description(action)}")
    lines.append("")
    lines.append("報告「逐等計畫」欄位：動作 = 代碼，說明 = 該等要做的事。")
    return "\n".join(lines)


def policy_label(policy: PolicyName) -> str:
    if policy is PolicyName.MP_WASH_SHORTFALL:
        return "A：不足時 MP wash (PerfectSin)"
    if policy is PolicyName.INT_DUMP_SHORTFALL:
        return "B：不足時全點 INT"
    if policy is PolicyName.MP_WASH_HARDCORE:
        return "C：硬核 A（≥12 MP 即洗；逐 AP 貪婪 HP1/MP1）"
    return policy.value


def format_optimize_report(result: OptimizeResult) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("MapleRoyals 盜賊洗血 — 政策比較")
    lines.append("=" * 72)

    a = result.comparison.policy_a
    b = result.comparison.policy_b
    c = result.comparison.policy_c
    lines.append("")
    lines.append("1) 政策比較（A vs B vs C）")
    lines.append("-" * 72)
    lines.append(_policy_block(policy_label(PolicyName.MP_WASH_SHORTFALL), a))
    lines.append(_policy_block(policy_label(PolicyName.INT_DUMP_SHORTFALL), b))
    lines.append(_policy_block(policy_label(PolicyName.MP_WASH_HARDCORE), c))

    if result.comparison.winner and result.comparison.apr_delta is not None:
        ranked = sorted(
            [x for x in (a, b, c) if x is not None],
            key=lambda cand: (
                0 if cand.reached_target else 1,
                cand.total_apr,
                -cand.final_display_hp,
            ),
        )
        runner_up = ranked[1] if len(ranked) > 1 else None
        if runner_up is not None:
            delta = result.comparison.apr_delta
            saved = -delta
            lines.append("")
            if saved > 0:
                delta_note = f"優勝方案較省 {saved} APR"
            else:
                delta_note = f"亞軍方案較省 {-saved} APR"
            lines.append(
                f"   優勝：{policy_label(result.comparison.winner.policy)}"
            )
            lines.append(
                f"   ΔAPR（優勝 − 亞軍）：{delta:+d}  （{delta_note}）"
            )
            if result.comparison.hp_delta is not None:
                lines.append(f"   ΔHP（優勝 − 亞軍）：{result.comparison.hp_delta:+d}")

    lines.append("")
    lines.append("2) 優勝方案")
    lines.append("-" * 72)
    lines.append(_winner_block(result.winner))

    lines.append("")
    lines.append("3) 前幾名候選")
    lines.append("-" * 72)
    if not result.top_candidates:
        lines.append("  （無）")
    else:
        lines.append(
            f"  {'#':>2}  {'政策':<22}  {'INT':>4}  {'達標等':>5}  {'mpEnd':>5}  "
            f"{'門檻':>4}  {'APR':>5}  {'HP':>6}  達標"
        )
        for i, c in enumerate(result.top_candidates, 1):
            short = {
                PolicyName.MP_WASH_SHORTFALL: "A_mp_wash",
                PolicyName.INT_DUMP_SHORTFALL: "B_int_dump",
                PolicyName.MP_WASH_HARDCORE: "C_hardcore",
            }.get(c.policy, c.policy.value)
            lines.append(
                f"  {i:>2}  {short:<22}  {c.target_base_int:>4}  "
                f"{c.int_reached_level:>5}  {c.mp_wash_end:>5}  "
                f"{extra_mp_threshold_short(c.policy, c.extra_mp_threshold):>4}  "
                f"{c.total_apr:>5}  {c.final_display_hp:>6}  "
                f"{'是' if c.reached_target else '否'}"
            )

    lines.append("")
    lines.append("4) 優勝方案逐等計畫（摘要）")
    lines.append("-" * 72)
    if result.winner is None or not result.winner.plan:
        lines.append("  （無計畫）")
    else:
        lines.extend(_plan_summary(result.winner))

    lines.append("")
    return "\n".join(lines)


def format_simulate_report(result: SimulateResult) -> str:
    cand = CandidateResult.from_simulate(result)
    lines = [
        "=" * 72,
        "MapleRoyals 盜賊洗血 — 模擬結果",
        "=" * 72,
        _winner_block(cand),
        "",
        "逐等計畫（摘要）",
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
        "action_desc",
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
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in plan_rows:
            writer.writerow(
                {
                    "level": row.level,
                    "action": row.action.value,
                    "action_desc": action_description(row.action),
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
        return f"  {title}：（未執行）"
    hit = "是" if c.reached_target else "否"
    return (
        f"  {title}：\n"
        f"    目標 base INT={c.target_base_int}  達標等級={c.int_reached_level}  "
        f"MP wash 結束={c.mp_wash_end}  {extra_mp_threshold_display(c.policy, c.extra_mp_threshold)}\n"
        f"    總 APR={c.total_apr}  最終 HP={c.final_display_hp}  達標={hit}\n"
        f"    APR 拆解：MP wash={c.apr.mp_wash_count}  Method1={c.apr.method1_hp_wash_count}  "
        f"Method2={c.apr.method2_hp_wash_count}  INT 洗回={c.apr.int_reset_apr}"
    )


def _winner_block(c: Optional[CandidateResult]) -> str:
    if c is None:
        return "  （無優勝方案）"
    return (
        f"  政策={policy_label(c.policy)}\n"
        f"  目標 base INT={c.target_base_int}\n"
        f"  達標等級={c.int_reached_level}  "
        f"（early 階段＝到目標 INT 為止，非固定等級）\n"
        f"  MP wash 結束等級={c.mp_wash_end}\n"
        f"  {extra_mp_threshold_display(c.policy, c.extra_mp_threshold)}\n"
        f"  base INT 峰值={c.base_int_peak}\n"
        f"  最終 base HP={c.final_base_hp}  最終顯示 HP={c.final_display_hp}\n"
        f"  是否達標={('是' if c.reached_target else '否')}\n"
        f"  總 APR={c.total_apr}\n"
        f"    MP wash={c.apr.mp_wash_count}\n"
        f"    Method1 HP wash={c.apr.method1_hp_wash_count}\n"
        f"    Method2 HP wash={c.apr.method2_hp_wash_count}\n"
        f"    INT 洗回 APR={c.apr.int_reset_apr}"
    )


def _plan_summary(c: CandidateResult) -> list[str]:
    lines: list[str] = []
    if not c.plan:
        return ["  （空白）"]
    lines.append(
        f"  {'等級':>4}  {'動作':<10}  {'說明':<36}  {'INT':>4}  {'LUK':>4}  {'HP':>6}  "
        f"{'MP':>5}  {'xMP':>5}  {'APR':>4}  備註"
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
            desc = action_description(row.action)
            if len(desc) > 36:
                desc = desc[:33] + "…"
            lines.append(
                f"  {row.level:>4}  {row.action.value:<10}  {desc:<36}  {row.base_int:>4}  "
                f"{row.base_luk:>4}  {row.base_hp:>6}  {row.base_mp:>5}  {row.extra_mp:>5}  "
                f"{row.apr_spent:>4}  {row.notes}"
            )
        prev_action = row.action
    lines.append(f"  （完整計畫共 {len(c.plan)} 列；請用 CSV 匯出查看全部）")
    return lines
