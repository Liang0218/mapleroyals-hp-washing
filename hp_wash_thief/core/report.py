"""Human-readable reports and CSV export (Traditional Chinese)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO, Union

from hp_wash_thief.core.models import (
    Action,
    CandidateResult,
    OptimizeResult,
    PolicyName,
    ResumeFrom,
    SimulateResult,
)


PLAN_CSV_HINT = "完整逐等計畫（每等動作與說明）請匯出 CSV 查看。"


@dataclass(frozen=True)
class ReportTable:
    title: str
    columns: tuple[str, ...]
    rows: list[tuple[str, ...]]


def policy_short(policy: PolicyName) -> str:
    return {
        PolicyName.MP_WASH_SHORTFALL: "A",
        PolicyName.INT_DUMP_SHORTFALL: "B",
        PolicyName.MP_WASH_HARDCORE: "C",
        PolicyName.INT_ONLY_PLAIN: "D",
    }.get(policy, policy.value)


def _comparison_slots(result: OptimizeResult) -> list[tuple[PolicyName, Optional[CandidateResult]]]:
    comp = result.comparison
    return [
        (PolicyName.MP_WASH_SHORTFALL, comp.policy_a),
        (PolicyName.INT_DUMP_SHORTFALL, comp.policy_b),
        (PolicyName.MP_WASH_HARDCORE, comp.policy_c),
        (PolicyName.INT_ONLY_PLAIN, comp.policy_d),
    ]


def comparison_letters(result: OptimizeResult) -> str:
    letters: list[str] = []
    for pol, cand in _comparison_slots(result):
        if cand is not None or pol in result.by_policy:
            letters.append(policy_short(pol))
    return " / ".join(letters) if letters else "—"


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
        Action.STR5: "5 點 AP 全點 STR（本等 0 wash APR）",
        Action.DEX5: "5 點 AP 全點 DEX（本等 0 wash APR）",
        Action.M2: "Method 2 補洗（APR MP → HP）",
        Action.RESET_INT: "INT 洗回 4，轉主屬性（消耗 INT 洗回 APR）",
        Action.RESUME: "中途接續起點（本列為輸入快照，尚未花本等 AP）",
    }
    return descriptions.get(action, action.value)


def extra_mp_threshold_display(policy: PolicyName, threshold: int) -> str:
    if policy is PolicyName.MP_WASH_HARDCORE:
        return "Extra MP 門檻=12（每次 HP wash；逐 AP 貪婪 HP1/MP1，非 60）"
    if policy is PolicyName.INT_ONLY_PLAIN:
        return "達標 INT 前僅堆 INT（early 階段 0 wash APR）"
    return f"Extra MP 門檻={threshold}（= 12×5，完整 HP wash×5）"


def extra_mp_threshold_short(policy: PolicyName, threshold: int) -> str:
    if policy is PolicyName.MP_WASH_HARDCORE:
        return "12/次"
    if policy is PolicyName.INT_ONLY_PLAIN:
        return "—"
    return str(threshold)


def format_ui_guide() -> str:
    """Desktop UI onboarding: tab purposes and recommended workflow."""
    return "\n".join(
        [
            "快速開始",
            "",
            "  1. 選擇職業（盜賊可比較 A–D；其他職業固定方案 D）",
            "  2. 裝備 Equipment — 設定裝備 INT（預設 0，請先做這步）",
            "  3. 最佳化 Optimize — 搜尋最低 APR（可設目標 HP／目標 MP）",
            "  4. 模擬 Simulate — 手動參數跑單一方案",
            "  5. 說明 Actions — 查動作代碼意思",
            "",
            "裝備填完請「儲存 JSON…」，下次「載入 JSON…」即可還原。",
            "改完直接按最佳化／模擬，會自動帶入智裝 INT。",
            "INT 洗回等級、reset 後智裝 INT 在 Optimize 參數列設定。",
            "目標 MP 留空＝洗到最低；有填則 200 等 base MP ≥ 目標（≥職業 min MP）。",
            "劍士／打手可覆寫 Improve MaxHP；中途接續填目前等級／HP／MP／INT。",
        ]
    )


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
        policy_label(PolicyName.INT_ONLY_PLAIN),
        "  達標 INT 前：30 等前 BUILD；31 等起 5 AP 全點 INT（不洗 HP/MP）。",
        "  達標 INT 後：與 A/B/C 相同（MP wash → HP wash → M2 → INT reset）。",
        "  非盜賊職業固定使用本政策（指南 Method2／堆 INT）。",
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
    if policy is PolicyName.INT_ONLY_PLAIN:
        return "D：純樸（達標 INT 前只堆 INT）"
    return policy.value


def policy_playbook(policy: PolicyName) -> str:
    """One-line in-game summary for the lazy pack."""
    if policy is PolicyName.MP_WASH_SHORTFALL:
        return "31 等起：Extra MP≥60 洗 HP×5，不足則 MP wash×5"
    if policy is PolicyName.INT_DUMP_SHORTFALL:
        return "31 等起：Extra MP≥60 洗 HP×5，不足則 5 AP 全點 INT"
    if policy is PolicyName.MP_WASH_HARDCORE:
        return "10 等起：每 AP 檢查 Extra MP≥12 洗 HP1；30+ 不足洗 MP1"
    if policy is PolicyName.INT_ONLY_PLAIN:
        return "達標 INT 前只堆 INT；達標後 MP wash→HP wash 洗到目標 HP"
    return policy.value


def _resume_block(resume: Optional[ResumeFrom], *, job: str = "thief") -> list[str]:
    if resume is None:
        return []
    from hp_wash_thief.core.formulas import extra_mp

    emp = int(round(extra_mp(resume.base_mp, resume.level, job)))
    fresh = resume.fresh_ap if resume.fresh_ap is not None else 5
    lines = [
        "【中途接續】",
        (
            f"  從 Lv{resume.level} 接續｜base HP {int(round(resume.base_hp))}｜"
            f"base MP {int(round(resume.base_mp))}（Extra MP≈{emp}）｜"
            f"INT {resume.base_int}｜LUK {resume.base_luk}｜DEX {resume.base_dex}"
        ),
        f"  尚未點的 AP {fresh}"
        + ("｜INT 已洗回" if resume.int_reset_done else "")
        + "｜下列 APR 為接續後剩餘",
        "",
    ]
    return lines


def _lazy_summary_optimize(result: OptimizeResult) -> list[str]:
    from hp_wash_thief.core.jobs import get_job_profile

    w = result.winner
    lines = ["【懶人包 — 照這樣做】", ""]
    job_for_resume = w.job if w is not None else (
        next(iter(result.by_policy.values())).job if result.by_policy else "thief"
    )
    lines.extend(_resume_block(result.resume_from, job=job_for_resume))
    if w is None:
        lines.append("  無可行方案。請調高目標 HP 上限、檢查裝備，或放寬搜尋範圍。")
        return lines

    job_name = get_job_profile(w.job).display_name_zh
    lines.append(f"  ★ 職業：{job_name}")
    lines.append(f"  ★ 最優政策：{policy_label(w.policy)}")
    lines.append(f"  ★ 怎麼洗：{policy_playbook(w.policy)}")
    key_bits = [
        f"base INT 堆到 {w.target_base_int}",
        f"MP wash 洗到 Lv{w.mp_wash_end}",
        f"約 Lv{w.int_reached_level} 前達標 INT",
    ]
    if w.improved_maxhp_level is not None:
        key_bits.append(f"ImproveMaxHP Lv{w.improved_maxhp_level}")
    lines.append("  ★ 關鍵參數：" + "｜".join(key_bits))
    hit = "有" if w.reached_target else "無"
    apr_label = "剩餘 APR" if result.resume_from else "總 APR"
    mp_bit = f"｜最終 MP {w.final_base_mp}"
    if w.target_mp is not None:
        mp_bit += f"（目標 ≥{w.target_mp}）"
    lines.append(
        f"  ★ 結果：{apr_label} {w.total_apr}｜最終 HP {w.final_display_hp}{mp_bit}｜達標={hit}"
    )

    comp = result.comparison
    if comp.winner and comp.apr_delta is not None and len(result.by_policy) > 1:
        saved = -comp.apr_delta
        if saved > 0:
            lines.append(f"  ★ 比次優省 {saved} APR")
        elif saved < 0:
            lines.append(f"  ★ 比次優多 {-saved} APR（仍為綜合最優）")

    lines.append("")
    lines.append("  完整逐等計畫請匯出 CSV 查看。")
    return lines


def _lazy_summary_simulate(c: CandidateResult) -> list[str]:
    from hp_wash_thief.core.jobs import get_job_profile

    lines = ["【懶人包 — 本方案】", ""]
    lines.extend(_resume_block(c.resume_from, job=c.job))
    lines.append(f"  ★ 職業：{get_job_profile(c.job).display_name_zh}")
    lines.append(f"  ★ 政策：{policy_label(c.policy)}")
    lines.append(f"  ★ 怎麼洗：{policy_playbook(c.policy)}")
    param = f"base INT 目標 {c.target_base_int}｜MP wash 至 Lv{c.mp_wash_end}"
    if c.improved_maxhp_level is not None:
        param += f"｜ImproveMaxHP Lv{c.improved_maxhp_level}"
    lines.append(f"  ★ 參數：{param}")
    hit = "有" if c.reached_target else "無"
    apr_label = "剩餘 APR" if c.resume_from else "總 APR"
    mp_bit = f"｜最終 MP {c.final_base_mp}"
    if c.target_mp is not None:
        mp_bit += f"（目標 ≥{c.target_mp}）"
    lines.append(
        f"  ★ 結果：{apr_label} {c.total_apr}｜最終 HP {c.final_display_hp}{mp_bit}｜達標={hit}"
    )
    lines.append("")
    return lines


def _comparison_notes(result: OptimizeResult) -> list[str]:
    lines: list[str] = []
    comp = result.comparison
    candidates = [c for _, c in _comparison_slots(result) if c is not None]
    if comp.winner and comp.apr_delta is not None and len(candidates) > 1:
        ranked = sorted(
            candidates,
            key=lambda cand: (
                0 if cand.reached_target else 1,
                cand.total_apr,
                -cand.final_display_hp,
            ),
        )
        runner_up = ranked[1] if len(ranked) > 1 else None
        if runner_up is not None:
            delta = comp.apr_delta
            saved = -delta
            lines.append("")
            lines.append(f"【{comparison_letters(result)} 勝負】")
            if saved > 0:
                delta_note = f"較次優省 {saved} APR"
            else:
                delta_note = f"較次優多 {-saved} APR"
            lines.append(f"  優勝：{policy_label(comp.winner.policy)}")
            lines.append(f"  ΔAPR：{delta:+d}（{delta_note}）")
            if comp.hp_delta is not None:
                lines.append(f"  ΔHP：{comp.hp_delta:+d}")
    return lines


def _candidate_row_values(c: CandidateResult) -> tuple[str, ...]:
    return (
        policy_short(c.policy),
        str(c.target_base_int),
        str(c.int_reached_level),
        str(c.mp_wash_end),
        str(c.total_apr),
        str(c.final_display_hp),
        "是" if c.reached_target else "否",
    )


def build_optimize_tables(result: OptimizeResult) -> list[ReportTable]:
    tables: list[ReportTable] = []
    compare_cols = (
        "政策",
        "目標INT",
        "達標等級",
        "洗MP結束等級",
        "總APR",
        "最終HP",
        "達標",
    )
    compare_rows: list[tuple[str, ...]] = []
    for pol, cand in _comparison_slots(result):
        if cand is None:
            compare_rows.append((policy_short(pol), "—", "—", "—", "—", "—", "未執行"))
        else:
            compare_rows.append(_candidate_row_values(cand))
    title = f"政策比較（{comparison_letters(result)}）"
    tables.append(ReportTable(title, compare_cols, compare_rows))

    if result.top_candidates:
        rank_cols = ("#",) + compare_cols
        rank_rows: list[tuple[str, ...]] = []
        for i, cand in enumerate(result.top_candidates, 1):
            rank_rows.append((str(i),) + _candidate_row_values(cand))
        tables.append(ReportTable("前幾名候選", rank_cols, rank_rows))
    return tables


def format_optimize_summary_text(result: OptimizeResult) -> str:
    lines: list[str] = []
    lines.extend(_lazy_summary_optimize(result))
    lines.extend(_comparison_notes(result))
    lines.append("")
    lines.append("【優勝方案詳情】")
    lines.append(_winner_block(result.winner))
    lines.append("")
    lines.append(f"【逐等計畫】{PLAN_CSV_HINT}")
    return "\n".join(lines)


def format_simulate_summary_text(result: SimulateResult) -> str:
    cand = CandidateResult.from_simulate(result)
    lines: list[str] = []
    lines.extend(_lazy_summary_simulate(cand))
    lines.append("【詳細參數】")
    lines.append(_winner_block(cand))
    lines.append("")
    lines.append(f"【逐等計畫】{PLAN_CSV_HINT}")
    return "\n".join(lines)


def format_optimize_report(result: OptimizeResult) -> str:
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("MapleRoyals 洗血 — 最佳化結果")
    lines.append("=" * 60)
    lines.extend(_lazy_summary_optimize(result))

    letters = comparison_letters(result)
    lines.append("")
    lines.append(f"1) 政策比較（{letters.replace(' / ', ' vs ')}）")
    lines.append("-" * 60)
    for pol, cand in _comparison_slots(result):
        if pol in result.by_policy or cand is not None:
            lines.append(_policy_block(policy_label(pol), cand))
    lines.extend(_comparison_notes(result))

    lines.append("")
    lines.append("2) 優勝方案")
    lines.append("-" * 60)
    lines.append(_winner_block(result.winner))

    if result.top_candidates:
        lines.append("")
        lines.append("3) 前幾名候選")
        lines.append("-" * 60)
        for i, cand in enumerate(result.top_candidates, 1):
            lines.append(
                f"  {i}. {policy_short(cand.policy)}  INT={cand.target_base_int}  "
                f"APR={cand.total_apr}  HP={cand.final_display_hp}  "
                f"達標={'是' if cand.reached_target else '否'}"
            )

    lines.append("")
    lines.append(f"4) {PLAN_CSV_HINT}")
    lines.append("")
    return "\n".join(lines)


def format_simulate_report(result: SimulateResult) -> str:
    lines = [
        "=" * 60,
        "MapleRoyals 洗血 — 模擬結果",
        "=" * 60,
        format_simulate_summary_text(result),
        "",
    ]
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
        "fresh_ap_str",
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
                    "fresh_ap_str": row.fresh_ap_str,
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
    from hp_wash_thief.core.jobs import get_job_profile

    job_line = f"  職業={get_job_profile(c.job).display_name_zh}\n"
    skill_line = ""
    if c.improved_maxhp_level is not None:
        skill_line = f"  Improve MaxHP 等級={c.improved_maxhp_level}\n"
    mp_target_line = ""
    if c.target_mp is not None:
        mp_target_line = f"  目標 base MP={c.target_mp}\n"
    return (
        job_line
        + f"  政策={policy_label(c.policy)}\n"
        f"  目標 base INT={c.target_base_int}\n"
        f"  達標等級={c.int_reached_level}  "
        f"（early 階段＝到目標 INT 為止，非固定等級）\n"
        f"  MP wash 結束等級={c.mp_wash_end}\n"
        f"  {extra_mp_threshold_display(c.policy, c.extra_mp_threshold)}\n"
        f"  INT reset 後 int_gear={c.int_gear_after_reset}\n"
        + skill_line
        + mp_target_line
        + f"  base INT 峰值={c.base_int_peak}\n"
        f"  最終 base HP={c.final_base_hp}  最終顯示 HP={c.final_display_hp}\n"
        f"  最終 base MP={c.final_base_mp}\n"
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
    lines.append("  Lv   Action        INT  LUK      HP     MP  xMP APR")
    lines.append("  " + "-" * 52)
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
                f"  {row.level:>3}  {row.action.value:<12}  "
                f"{row.base_int:>4}  {row.base_luk:>4}  {row.base_hp:>6}  "
                f"{row.base_mp:>5}  {row.extra_mp:>4}  {row.apr_spent:>3}"
            )
            desc = action_description(row.action)
            extras: list[str] = []
            if desc:
                extras.append(desc)
            if row.notes:
                extras.append(row.notes)
            if extras:
                lines.append(f"       → {'｜'.join(extras)}")
        prev_action = row.action
    lines.append(f"  （完整計畫共 {len(c.plan)} 列；請用 CSV 匯出查看全部）")
    return lines
