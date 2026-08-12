"""CustomTkinter desktop UI for the multi-job HP wash optimizer (Traditional Chinese).

All wash logic stays in ``hp_wash_thief.core.api``; this module only collects
inputs and displays reports/CSV.
"""

from __future__ import annotations

import threading
import traceback
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from hp_wash_thief.core.api import optimize, simulate
from hp_wash_thief.core.jobs import JobId, get_job_profile
from hp_wash_thief.core.models import HpMode, OptimizeConfig, PolicyName, ResumeFrom, SimulateConfig
from hp_wash_thief.core.report import (
    PLAN_CSV_HINT,
    build_optimize_tables,
    format_action_legend,
    format_optimize_summary_text,
    format_simulate_summary_text,
    format_ui_guide,
    write_plan_csv,
)
from hp_wash_thief.ui.equipment_panel import EquipmentPanel
from hp_wash_thief.ui.result_panel import ResultPanel
from hp_wash_thief.ui.user_errors import format_user_error
from hp_wash_thief.ui.resources import default_csv_path

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

# Display label → internal value
HP_MODE_LABELS = {
    "平均 (avg)": "avg",
    "最小 (min)": "min",
    "最大 (max)": "max",
}
JOB_LABELS = {
    "盜賊 Thief": "thief",
    "弓箭手 Bowman": "bowman",
    "槍手 Gunslinger": "gunslinger",
    "打手 Brawler": "brawler",
    "劍士 Fighter": "fighter",
    "準騎士 Page": "page",
    "槍戰士 Spearman": "spearman",
    "初心者 Beginner": "beginner",
}
JOB_VALUE_TO_LABEL = {v: k for k, v in JOB_LABELS.items()}
OPT_POLICY_LABELS = {
    "依職業自動": "auto",
    "四種都跑 (ABCD)": "all",
    "三種都跑 (ABD)": "abd",
    "A：不足時 MP wash": "mp_wash_shortfall",
    "B：不足時全點 INT": "int_dump_shortfall",
    "C：硬核 A（≥12 逐 AP；30+ MP1）": "mp_wash_hardcore",
    "D：純樸（達標 INT 前只堆 INT）": "int_only_plain",
}
SIM_POLICY_LABELS = {
    "依職業自動": "auto",
    "A：不足時 MP wash": "mp_wash_shortfall",
    "B：不足時全點 INT": "int_dump_shortfall",
    "C：硬核 A（≥12 逐 AP；30+ MP1）": "mp_wash_hardcore",
    "D：純樸（達標 INT 前只堆 INT）": "int_only_plain",
}


class HpWashApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MapleRoyals 洗血 APR 最佳化")
        self.geometry("1100x780")
        self.minsize(920, 640)

        self._worker: Optional[threading.Thread] = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="MapleRoyals 洗血 APR 最佳化（多職業）",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        header.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 6))

        body = ctk.CTkTabview(self)
        self._tabview = body
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.tab_guide = body.add("操作說明 Guide")
        self.tab_equip = body.add("裝備 Equipment")
        self.tab_opt = body.add("最佳化 Optimize")
        self.tab_sim = body.add("模擬 Simulate")
        self.tab_help = body.add("說明 Actions")
        self.tab_guide.grid_columnconfigure(0, weight=1)
        self.tab_guide.grid_rowconfigure(1, weight=1)
        self.tab_opt.grid_columnconfigure(0, weight=1)
        self.tab_opt.grid_rowconfigure(3, weight=1)
        self.tab_sim.grid_columnconfigure(0, weight=1)
        self.tab_sim.grid_rowconfigure(3, weight=1)
        self.tab_equip.grid_columnconfigure(0, weight=1)
        self.tab_equip.grid_rowconfigure(0, weight=1)
        self.tab_help.grid_columnconfigure(0, weight=1)
        self.tab_help.grid_rowconfigure(1, weight=1)

        self._build_guide_tab(self.tab_guide)

        # Equipment preview reads int_reset_level from Optimize params — build those first.
        self._build_shared_params(self.tab_opt, prefix="opt")

        self._equipment_panel = EquipmentPanel(
            self.tab_equip,
            get_int_reset_level=self._equipment_int_reset_level,
            get_int_gear_after_reset=self._equipment_int_gear_after_reset,
        )
        self._equipment_panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self._build_help_tab(self.tab_help)

        self._build_optimize_extra(self.tab_opt)
        self._build_resume_panel(self.tab_opt, prefix="opt")
        self._build_output_panel(self.tab_opt, prefix="opt")
        self._build_actions(
            self.tab_opt, prefix="opt", run_label="執行最佳化", command=self._run_optimize
        )

        self._build_shared_params(self.tab_sim, prefix="sim")
        self._build_simulate_extra(self.tab_sim)
        self._build_resume_panel(self.tab_sim, prefix="sim")
        self._build_output_panel(self.tab_sim, prefix="sim")
        self._build_actions(
            self.tab_sim, prefix="sim", run_label="執行模擬", command=self._run_simulate
        )

        self._equipment_panel.load_defaults()
        self._bind_gear_param_refresh()

    def _bind_gear_param_refresh(self) -> None:
        """Refresh equipment INT preview when reset-related params change."""

        def refresh_from_opt(_event=None) -> None:
            self._equipment_panel.refresh_preview(
                int_reset_level=self._equipment_int_reset_level(),
                int_gear_after_reset=self._equipment_int_gear_after_reset(),
            )

        def refresh_from_sim(_event=None) -> None:
            try:
                reset = int(self.sim_int_reset_level.get().strip())
            except ValueError:
                return
            try:
                after = int(self.sim_int_gear_after_reset.get().strip())
            except ValueError:
                after = None
            self._equipment_panel.refresh_preview(
                int_reset_level=reset,
                int_gear_after_reset=after,
            )

        for entry in (self.opt_int_reset_level, self.opt_int_gear_after_reset):
            entry.bind("<KeyRelease>", refresh_from_opt)
            entry.bind("<FocusOut>", refresh_from_opt)
        for entry in (self.sim_int_reset_level, self.sim_int_gear_after_reset):
            entry.bind("<KeyRelease>", refresh_from_sim)
            entry.bind("<FocusOut>", refresh_from_sim)

    def _build_guide_tab(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text="操作說明",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.grid(row=0, column=1, sticky="e", padx=12, pady=(12, 6))
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row,
            text="前往裝備設定 →",
            width=160,
            command=lambda: self._tabview.set("裝備 Equipment"),
        ).pack(side="right")

        box = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family="Microsoft JhengHei UI", size=14),
        )
        box.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))
        box.insert("1.0", format_ui_guide())
        box.configure(state="disabled")

    def _build_help_tab(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text="政策與動作代碼說明（逐等計畫請匯出 CSV，欄位含 action_desc）",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
        box = ctk.CTkTextbox(parent, font=ctk.CTkFont(family="Microsoft JhengHei UI", size=13))
        box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        box.insert("1.0", format_action_legend())
        box.configure(state="disabled")

    def _build_shared_params(self, parent: ctk.CTkFrame, *, prefix: str) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        for col in range(6):
            frame.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(frame, text="職業").grid(row=0, column=0, sticky="w", padx=6, pady=(8, 0))
        job_menu = ctk.CTkOptionMenu(
            frame,
            values=list(JOB_LABELS.keys()),
            command=lambda _v, p=prefix: self._on_job_changed(p),
        )
        job_menu.set("盜賊 Thief")
        job_menu.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_job", job_menu)

        ctk.CTkLabel(frame, text="Improve MaxHP（可空＝自動）").grid(
            row=0, column=1, sticky="w", padx=6, pady=(8, 0)
        )
        skill = ctk.CTkEntry(frame, placeholder_text="0–10 或留空")
        skill.grid(row=1, column=1, sticky="ew", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_improved_maxhp_level", skill)

        fields = [
            ("target_hp", "目標 HP", "27000", 2),
            ("int_reset_level", "INT 洗回等級", "155", 3),
            ("int_gear_after_reset", "INT reset 後 int_gear", "50", 4),
            ("quest_equip_hp", "任務／裝備 HP", "0", 5),
        ]
        for key, label, default, col in fields:
            ctk.CTkLabel(frame, text=label).grid(
                row=0, column=col, sticky="w", padx=6, pady=(8, 0)
            )
            entry = ctk.CTkEntry(frame)
            entry.insert(0, default)
            entry.grid(row=1, column=col, sticky="ew", padx=6, pady=(0, 8))
            setattr(self, f"{prefix}_{key}", entry)

        ctk.CTkLabel(frame, text="MW（base INT 比例）").grid(
            row=2, column=0, sticky="w", padx=6
        )
        mw = ctk.CTkEntry(frame)
        mw.insert(0, "0.10")
        mw.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_mw_percent", mw)

        ctk.CTkLabel(frame, text="MW 起始等級").grid(row=2, column=1, sticky="w", padx=6)
        mw_from = ctk.CTkEntry(frame)
        mw_from.insert(0, "10")
        mw_from.grid(row=3, column=1, sticky="ew", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_mw_from_level", mw_from)

        ctk.CTkLabel(frame, text="HP 模式").grid(row=2, column=2, sticky="w", padx=6)
        mode = ctk.CTkOptionMenu(frame, values=list(HP_MODE_LABELS.keys()))
        mode.set("平均 (avg)")
        mode.grid(row=3, column=2, sticky="ew", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_hp_mode", mode)

        gear_note = ctk.CTkLabel(
            frame,
            text="INT 裝備由「裝備 Equipment」分頁自動帶入｜非盜賊固定方案 D（Method2）",
            text_color=("gray30", "gray70"),
        )
        gear_note.grid(row=3, column=3, columnspan=3, sticky="w", padx=6, pady=(0, 8))
        self._on_job_changed(prefix)

    def _selected_job(self, prefix: str) -> str:
        label = getattr(self, f"{prefix}_job").get()
        return JOB_LABELS.get(label, "thief")

    def _on_job_changed(self, prefix: str) -> None:
        job = self._selected_job(prefix)
        profile = get_job_profile(job)
        is_thief = job == JobId.THIEF.value
        skill_entry = getattr(self, f"{prefix}_improved_maxhp_level", None)
        if skill_entry is not None:
            if profile.maxhp_skill is None:
                skill_entry.delete(0, "end")
                skill_entry.configure(state="disabled", placeholder_text="此職業無此技能")
            else:
                skill_entry.configure(state="normal", placeholder_text="0–10 或留空＝自動")

        if prefix == "opt" and hasattr(self, "opt_policies"):
            if is_thief:
                self.opt_policies.configure(values=list(OPT_POLICY_LABELS.keys()))
                self.opt_policies.set("依職業自動")
                self.opt_policies.configure(state="normal")
            else:
                self.opt_policies.configure(values=["依職業自動（僅 D）"])
                self.opt_policies.set("依職業自動（僅 D）")
                self.opt_policies.configure(state="disabled")
        if prefix == "sim" and hasattr(self, "sim_policy"):
            if is_thief:
                self.sim_policy.configure(values=list(SIM_POLICY_LABELS.keys()))
                self.sim_policy.set("依職業自動")
                self.sim_policy.configure(state="normal")
            else:
                self.sim_policy.configure(values=["依職業自動（僅 D）"])
                self.sim_policy.set("依職業自動（僅 D）")
                self.sim_policy.configure(state="disabled")

    def _build_optimize_extra(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="政策").grid(row=0, column=0, sticky="w", padx=6, pady=8)
        policies = ctk.CTkOptionMenu(frame, values=list(OPT_POLICY_LABELS.keys()))
        policies.set("依職業自動")
        policies.grid(row=0, column=1, sticky="w", padx=6, pady=8)
        self.opt_policies = policies

        ctk.CTkLabel(frame, text="保留前 N 名").grid(row=0, column=2, sticky="w", padx=6, pady=8)
        top = ctk.CTkEntry(frame, width=80)
        top.insert(0, "5")
        top.grid(row=0, column=3, sticky="w", padx=6, pady=8)
        self.opt_top = top
        self._on_job_changed("opt")

    def _build_simulate_extra(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        for col in range(6):
            frame.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(frame, text="政策").grid(row=0, column=0, sticky="w", padx=6)
        policy = ctk.CTkOptionMenu(frame, values=list(SIM_POLICY_LABELS.keys()))
        policy.set("依職業自動")
        policy.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 8))
        self.sim_policy = policy

        specs = [
            ("target_base_int", "目標 base INT", "350"),
            ("mp_wash_end", "MP wash 結束等級", "100"),
        ]
        for i, (key, label, default) in enumerate(specs, start=1):
            ctk.CTkLabel(frame, text=label).grid(row=0, column=i, sticky="w", padx=6)
            entry = ctk.CTkEntry(frame)
            entry.insert(0, default)
            entry.grid(row=1, column=i, sticky="ew", padx=6, pady=(0, 8))
            setattr(self, f"sim_{key}", entry)

        auto_m2 = ctk.CTkCheckBox(frame, text="自動 Method 2 補洗")
        auto_m2.select()
        auto_m2.grid(row=1, column=4, sticky="w", padx=6, pady=(0, 8))
        self.sim_auto_method2 = auto_m2
        self._on_job_changed("sim")

    def _build_resume_panel(self, parent: ctk.CTkFrame, *, prefix: str) -> None:
        """Optional mid-game snapshot: continue from current level/stats."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        for col in range(6):
            frame.grid_columnconfigure(col, weight=1)

        enabled = ctk.CTkCheckBox(
            frame,
            text="中途接續（填目前等級／HP／MP／INT，從尚未點的 AP 起算最省路徑）",
            command=lambda p=prefix: self._toggle_resume(p),
        )
        enabled.grid(row=0, column=0, columnspan=6, sticky="w", padx=6, pady=(8, 4))
        setattr(self, f"{prefix}_resume_enabled", enabled)

        fields = [
            ("from_level", "目前等級", ""),
            ("base_hp", "base HP（APR 顯示的數值）", ""),
            ("base_mp", "base MP（APR 顯示的數值）", ""),
            ("base_int", "base INT", ""),
            ("base_luk", "base LUK", "4"),
            ("base_dex", "base DEX", "25"),
        ]
        for i, (key, label, default) in enumerate(fields):
            ctk.CTkLabel(frame, text=label).grid(row=1, column=i, sticky="w", padx=6)
            entry = ctk.CTkEntry(frame)
            if default:
                entry.insert(0, default)
            entry.grid(row=2, column=i, sticky="ew", padx=6, pady=(0, 4))
            setattr(self, f"{prefix}_resume_{key}", entry)

        more = [
            ("fresh_ap", "尚未點的 AP", "5"),
        ]
        for i, (key, label, default) in enumerate(more):
            ctk.CTkLabel(frame, text=label).grid(row=3, column=i, sticky="w", padx=6)
            entry = ctk.CTkEntry(frame)
            entry.insert(0, default)
            entry.grid(row=4, column=i, sticky="ew", padx=6, pady=(0, 8))
            setattr(self, f"{prefix}_resume_{key}", entry)

        reset_done = ctk.CTkCheckBox(frame, text="INT 已洗回（base INT=4）")
        reset_done.grid(row=4, column=1, sticky="w", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_resume_int_reset_done", reset_done)

        note = ctk.CTkLabel(
            frame,
            text="語意：已升到該等；base HP／MP 請填 APR 視窗看到的數值。報告 APR 為接續後剩餘。",
            text_color=("gray30", "gray70"),
        )
        note.grid(row=5, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 8))
        self._toggle_resume(prefix)

    def _toggle_resume(self, prefix: str) -> None:
        enabled = bool(getattr(self, f"{prefix}_resume_enabled").get())
        state = "normal" if enabled else "disabled"
        for key in (
            "from_level",
            "base_hp",
            "base_mp",
            "base_int",
            "base_luk",
            "base_dex",
            "fresh_ap",
        ):
            getattr(self, f"{prefix}_resume_{key}").configure(state=state)
        getattr(self, f"{prefix}_resume_int_reset_done").configure(state=state)

    def _build_output_panel(self, parent: ctk.CTkFrame, *, prefix: str) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="CSV 輸出路徑（可留空）").grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 0)
        )
        csv_row = ctk.CTkFrame(frame, fg_color="transparent")
        csv_row.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        csv_row.grid_columnconfigure(0, weight=1)
        csv_entry = ctk.CTkEntry(csv_row)
        csv_entry.insert(0, str(default_csv_path()))
        csv_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        setattr(self, f"{prefix}_csv", csv_entry)
        ctk.CTkButton(
            csv_row, text="瀏覽…", width=90, command=lambda: self._browse_csv(prefix)
        ).grid(row=0, column=1)

        ctk.CTkLabel(frame, text="結果").grid(row=2, column=0, sticky="w", padx=8, pady=(8, 0))
        result = ResultPanel(frame)
        result.grid(row=3, column=0, sticky="nsew", padx=8, pady=(4, 8))
        frame.grid_rowconfigure(3, weight=1)
        setattr(self, f"{prefix}_result", result)

    def _build_actions(self, parent: ctk.CTkFrame, *, prefix: str, run_label: str, command) -> None:
        bar = ctk.CTkFrame(parent)
        bar.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        run_btn = ctk.CTkButton(bar, text=run_label, command=command, width=160)
        run_btn.pack(side="left", padx=6, pady=8)
        setattr(self, f"{prefix}_run_btn", run_btn)
        status = ctk.CTkLabel(bar, text="就緒")
        status.pack(side="left", padx=10)
        setattr(self, f"{prefix}_status", status)

    def _equipment_int_reset_level(self) -> int:
        entry = getattr(self, "opt_int_reset_level", None)
        if entry is None:
            return 155
        try:
            return int(entry.get().strip())
        except ValueError:
            return 155

    def _equipment_int_gear_after_reset(self) -> int:
        entry = getattr(self, "opt_int_gear_after_reset", None)
        if entry is None:
            return 50
        try:
            return int(entry.get().strip())
        except ValueError:
            return 50

    def _browse_csv(self, prefix: str) -> None:
        path = filedialog.asksaveasfilename(
            title="選擇 CSV 輸出路徑",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        entry = getattr(self, f"{prefix}_csv")
        entry.delete(0, "end")
        entry.insert(0, path)

    def _int(self, entry: ctk.CTkEntry, name: str) -> int:
        try:
            return int(entry.get().strip())
        except ValueError as exc:
            raise ValueError(f"「{name}」必須是整數") from exc

    def _float(self, entry: ctk.CTkEntry, name: str) -> float:
        try:
            return float(entry.get().strip())
        except ValueError as exc:
            raise ValueError(f"「{name}」必須是數字") from exc

    def _shared_kwargs(self, prefix: str) -> dict:
        mode_label = getattr(self, f"{prefix}_hp_mode").get()
        mode_value = HP_MODE_LABELS.get(mode_label, mode_label)
        int_reset_level = self._int(
            getattr(self, f"{prefix}_int_reset_level"), "INT 洗回等級"
        )
        int_gear_after_reset = self._int(
            getattr(self, f"{prefix}_int_gear_after_reset"), "INT reset 後 int_gear"
        )
        skill_raw = getattr(self, f"{prefix}_improved_maxhp_level").get().strip()
        improved_maxhp_level = None
        if skill_raw:
            improved_maxhp_level = self._int(
                getattr(self, f"{prefix}_improved_maxhp_level"), "Improve MaxHP 等級"
            )
            if not (0 <= improved_maxhp_level <= 10):
                raise ValueError("Improve MaxHP 等級須為 0–10。")
        return {
            "job": self._selected_job(prefix),
            "target_hp": self._int(getattr(self, f"{prefix}_target_hp"), "目標 HP"),
            "int_reset_level": int_reset_level,
            "int_gear_after_reset": int_gear_after_reset,
            "quest_equip_hp": self._int(
                getattr(self, f"{prefix}_quest_equip_hp"), "任務／裝備 HP"
            ),
            "mw_percent": self._float(getattr(self, f"{prefix}_mw_percent"), "MW 比例"),
            "mw_from_level": self._int(
                getattr(self, f"{prefix}_mw_from_level"), "MW 起始等級"
            ),
            "hp_mode": HpMode(mode_value),
            "int_gear": self._equipment_panel.current_int_gear_segments(
                int_reset_level=int_reset_level
            ),
            "improved_maxhp_level": improved_maxhp_level,
        }

    def _set_busy(self, prefix: str, busy: bool, message: str = "") -> None:
        btn = getattr(self, f"{prefix}_run_btn")
        status = getattr(self, f"{prefix}_status")
        btn.configure(state="disabled" if busy else "normal")
        status.configure(text=message or ("計算中…" if busy else "就緒"))

    def _show_result(self, prefix: str, summary: str, tables, footer: str = "") -> None:
        panel = getattr(self, f"{prefix}_result")
        panel.show(summary, tables, footer)

    def _run_in_thread(self, prefix: str, fn) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("忙碌中", "目前已有工作在執行，請稍候。")
            return

        def worker() -> None:
            try:
                self.after(0, lambda: self._set_busy(prefix, True))
                summary, tables, csv_msg = fn()

                def ok() -> None:
                    self._show_result(prefix, summary, tables, csv_msg)
                    self._set_busy(prefix, False, "完成")

                self.after(0, ok)
            except Exception as exc:  # noqa: BLE001
                user_msg = format_user_error(exc)
                detail = ""
                if not isinstance(exc, (ValueError, RuntimeError, OSError)):
                    detail = traceback.format_exc()

                def fail() -> None:
                    getattr(self, f"{prefix}_result").show_error(user_msg, detail)
                    self._set_busy(prefix, False, "錯誤")
                    messagebox.showerror("錯誤", user_msg)

                self.after(0, fail)

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _parse_resume(self, prefix: str) -> Optional[ResumeFrom]:
        if not bool(getattr(self, f"{prefix}_resume_enabled").get()):
            return None
        level = self._int(getattr(self, f"{prefix}_resume_from_level"), "目前等級")
        base_hp = self._float(
            getattr(self, f"{prefix}_resume_base_hp"), "base HP（APR 顯示的數值）"
        )
        base_mp = self._float(
            getattr(self, f"{prefix}_resume_base_mp"), "base MP（APR 顯示的數值）"
        )
        base_int = self._int(getattr(self, f"{prefix}_resume_base_int"), "base INT")
        base_luk = self._int(getattr(self, f"{prefix}_resume_base_luk"), "base LUK")
        base_dex = self._int(getattr(self, f"{prefix}_resume_base_dex"), "base DEX")
        fresh_raw = getattr(self, f"{prefix}_resume_fresh_ap").get().strip()
        fresh_ap = int(fresh_raw) if fresh_raw else None
        return ResumeFrom.from_stats(
            level=level,
            base_hp=base_hp,
            base_mp=base_mp,
            base_int=base_int,
            base_luk=base_luk,
            base_dex=base_dex,
            fresh_ap=fresh_ap,
            int_reset_done=bool(getattr(self, f"{prefix}_resume_int_reset_done").get()),
            job=self._selected_job(prefix),
        )

    def _parse_opt_policies(self, job: str) -> list[PolicyName]:
        raw_label = self.opt_policies.get()
        policies_raw = OPT_POLICY_LABELS.get(raw_label, raw_label)
        if policies_raw in ("auto", "依職業自動（僅 D）") or "僅 D" in raw_label:
            return list(get_job_profile(job).policies)
        if policies_raw == "all":
            return [
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.MP_WASH_HARDCORE,
                PolicyName.INT_ONLY_PLAIN,
            ]
        if policies_raw == "abd":
            return [
                PolicyName.MP_WASH_SHORTFALL,
                PolicyName.INT_DUMP_SHORTFALL,
                PolicyName.INT_ONLY_PLAIN,
            ]
        return [PolicyName(policies_raw)]

    def _run_optimize(self) -> None:
        def job():
            shared = self._shared_kwargs("opt")
            config = OptimizeConfig(
                target_hp=shared["target_hp"],
                int_reset_level=shared["int_reset_level"],
                int_gear=shared["int_gear"],
                job=shared["job"],
                int_gear_after_reset=shared["int_gear_after_reset"],
                policies=self._parse_opt_policies(shared["job"]),
                quest_equip_hp=shared["quest_equip_hp"],
                hp_mode=shared["hp_mode"],
                mw_percent=shared["mw_percent"],
                mw_from_level=shared["mw_from_level"],
                top_n=self._int(self.opt_top, "保留前 N 名"),
                resume_from=self._parse_resume("opt"),
                improved_maxhp_level=shared["improved_maxhp_level"],
            )
            result = optimize(config)
            summary = format_optimize_summary_text(result)
            tables = build_optimize_tables(result)
            csv_path = self.opt_csv.get().strip()
            csv_msg = ""
            if csv_path:
                if result.winner is None or not result.winner.plan:
                    csv_msg = "無優勝方案，未寫入 CSV。"
                else:
                    write_plan_csv(result.winner.plan, csv_path)
                    csv_msg = f"已寫入優勝計畫 CSV：{csv_path}"
            elif result.winner and result.winner.plan:
                csv_msg = PLAN_CSV_HINT
            return summary, tables, csv_msg

        self._run_in_thread("opt", job)

    def _run_simulate(self) -> None:
        def job():
            shared = self._shared_kwargs("sim")
            policy_label = self.sim_policy.get()
            policy_raw = SIM_POLICY_LABELS.get(policy_label, policy_label)
            if policy_raw in ("auto",) or "僅 D" in policy_label:
                policy = get_job_profile(shared["job"]).policies[0]
            else:
                policy = PolicyName(policy_raw)
            config = SimulateConfig(
                policy=policy,
                target_base_int=self._int(self.sim_target_base_int, "目標 base INT"),
                target_hp=shared["target_hp"],
                int_reset_level=shared["int_reset_level"],
                int_gear=shared["int_gear"],
                job=shared["job"],
                int_gear_after_reset=shared["int_gear_after_reset"],
                mp_wash_end=self._int(self.sim_mp_wash_end, "MP wash 結束等級"),
                quest_equip_hp=shared["quest_equip_hp"],
                hp_mode=shared["hp_mode"],
                auto_method2=bool(self.sim_auto_method2.get()),
                mw_percent=shared["mw_percent"],
                mw_from_level=shared["mw_from_level"],
                resume_from=self._parse_resume("sim"),
                improved_maxhp_level=shared["improved_maxhp_level"],
            )
            result = simulate(config)
            summary = format_simulate_summary_text(result)
            csv_path = self.sim_csv.get().strip()
            csv_msg = ""
            if csv_path:
                write_plan_csv(result.plan, csv_path)
                csv_msg = f"已寫入計畫 CSV：{csv_path}"
            elif result.plan:
                csv_msg = PLAN_CSV_HINT
            return summary, [], csv_msg

        self._run_in_thread("sim", job)


def run_app() -> None:
    app = HpWashApp()
    app.mainloop()


def main() -> int:
    run_app()
    return 0
