"""CustomTkinter desktop UI for the Thief HP wash optimizer (Traditional Chinese).

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
from hp_wash_thief.core.models import HpMode, OptimizeConfig, PolicyName, SimulateConfig
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
OPT_POLICY_LABELS = {
    "三種都跑 (ABC)": "all",
    "兩種都跑 (AB)": "both",
    "A：不足時 MP wash": "mp_wash_shortfall",
    "B：不足時全點 INT": "int_dump_shortfall",
    "C：硬核 A（≥12 逐 AP；30+ MP1）": "mp_wash_hardcore",
}
SIM_POLICY_LABELS = {
    "A：不足時 MP wash": "mp_wash_shortfall",
    "B：不足時全點 INT": "int_dump_shortfall",
    "C：硬核 A（≥12 逐 AP；30+ MP1）": "mp_wash_hardcore",
}


class HpWashApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MapleRoyals 盜賊洗血 APR 最佳化")
        self.geometry("1100x780")
        self.minsize(920, 640)

        self._worker: Optional[threading.Thread] = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="MapleRoyals 盜賊洗血 APR 最佳化",
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
        self.tab_opt.grid_rowconfigure(2, weight=1)
        self.tab_sim.grid_columnconfigure(0, weight=1)
        self.tab_sim.grid_rowconfigure(2, weight=1)
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
        self._build_output_panel(self.tab_opt, prefix="opt")
        self._build_actions(
            self.tab_opt, prefix="opt", run_label="執行最佳化", command=self._run_optimize
        )

        self._build_shared_params(self.tab_sim, prefix="sim")
        self._build_simulate_extra(self.tab_sim)
        self._build_output_panel(self.tab_sim, prefix="sim")
        self._build_actions(
            self.tab_sim, prefix="sim", run_label="執行模擬", command=self._run_simulate
        )

        self._equipment_panel.load_defaults()

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

        fields = [
            ("target_hp", "目標 HP", "27000"),
            ("int_reset_level", "INT 洗回等級", "155"),
            ("int_gear_after_reset", "INT reset 後 int_gear", "50"),
            ("quest_equip_hp", "任務／裝備 HP", "0"),
            ("mw_percent", "MW（base INT 比例）", "0.10"),
            ("mw_from_level", "MW 起始等級", "10"),
        ]
        for i, (key, label, default) in enumerate(fields):
            ctk.CTkLabel(frame, text=label).grid(row=0, column=i, sticky="w", padx=6, pady=(8, 0))
            entry = ctk.CTkEntry(frame)
            entry.insert(0, default)
            entry.grid(row=1, column=i, sticky="ew", padx=6, pady=(0, 8))
            setattr(self, f"{prefix}_{key}", entry)

        ctk.CTkLabel(frame, text="HP 模式").grid(row=2, column=0, sticky="w", padx=6)
        mode = ctk.CTkOptionMenu(frame, values=list(HP_MODE_LABELS.keys()))
        mode.set("平均 (avg)")
        mode.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 8))
        setattr(self, f"{prefix}_hp_mode", mode)

        gear_note = ctk.CTkLabel(
            frame,
            text="INT 裝備由「裝備 Equipment」分頁自動帶入（無需 JSON）",
            text_color=("gray30", "gray70"),
        )
        gear_note.grid(row=3, column=1, columnspan=5, sticky="w", padx=6, pady=(0, 8))

    def _build_optimize_extra(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="政策").grid(row=0, column=0, sticky="w", padx=6, pady=8)
        policies = ctk.CTkOptionMenu(frame, values=list(OPT_POLICY_LABELS.keys()))
        policies.set("三種都跑 (ABC)")
        policies.grid(row=0, column=1, sticky="w", padx=6, pady=8)
        self.opt_policies = policies

        ctk.CTkLabel(frame, text="保留前 N 名").grid(row=0, column=2, sticky="w", padx=6, pady=8)
        top = ctk.CTkEntry(frame, width=80)
        top.insert(0, "5")
        top.grid(row=0, column=3, sticky="w", padx=6, pady=8)
        self.opt_top = top

    def _build_simulate_extra(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        for col in range(5):
            frame.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(frame, text="政策").grid(row=0, column=0, sticky="w", padx=6)
        policy = ctk.CTkOptionMenu(frame, values=list(SIM_POLICY_LABELS.keys()))
        policy.set("A：不足時 MP wash")
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
        auto_m2.grid(row=1, column=3, sticky="w", padx=6, pady=(0, 8))
        self.sim_auto_method2 = auto_m2

    def _build_output_panel(self, parent: ctk.CTkFrame, *, prefix: str) -> None:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
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
        bar.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
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
        return {
            "target_hp": self._int(getattr(self, f"{prefix}_target_hp"), "目標 HP"),
            "int_reset_level": self._int(
                getattr(self, f"{prefix}_int_reset_level"), "INT 洗回等級"
            ),
            "int_gear_after_reset": self._int(
                getattr(self, f"{prefix}_int_gear_after_reset"), "INT reset 後 int_gear"
            ),
            "quest_equip_hp": self._int(
                getattr(self, f"{prefix}_quest_equip_hp"), "任務／裝備 HP"
            ),
            "mw_percent": self._float(getattr(self, f"{prefix}_mw_percent"), "MW 比例"),
            "mw_from_level": self._int(
                getattr(self, f"{prefix}_mw_from_level"), "MW 起始等級"
            ),
            "hp_mode": HpMode(mode_value),
            "int_gear": self._equipment_panel.current_int_gear_segments(),
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

    def _run_optimize(self) -> None:
        def job():
            shared = self._shared_kwargs("opt")
            policies_raw = OPT_POLICY_LABELS.get(
                self.opt_policies.get(), self.opt_policies.get()
            )
            if policies_raw == "all":
                policies = [
                    PolicyName.MP_WASH_SHORTFALL,
                    PolicyName.INT_DUMP_SHORTFALL,
                    PolicyName.MP_WASH_HARDCORE,
                ]
            elif policies_raw == "both":
                policies = [PolicyName.MP_WASH_SHORTFALL, PolicyName.INT_DUMP_SHORTFALL]
            else:
                policies = [PolicyName(policies_raw)]
            config = OptimizeConfig(
                target_hp=shared["target_hp"],
                int_reset_level=shared["int_reset_level"],
                int_gear=shared["int_gear"],
                int_gear_after_reset=shared["int_gear_after_reset"],
                policies=policies,
                quest_equip_hp=shared["quest_equip_hp"],
                hp_mode=shared["hp_mode"],
                mw_percent=shared["mw_percent"],
                mw_from_level=shared["mw_from_level"],
                top_n=self._int(self.opt_top, "保留前 N 名"),
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
            policy_raw = SIM_POLICY_LABELS.get(self.sim_policy.get(), self.sim_policy.get())
            config = SimulateConfig(
                policy=PolicyName(policy_raw),
                target_base_int=self._int(self.sim_target_base_int, "目標 base INT"),
                target_hp=shared["target_hp"],
                int_reset_level=shared["int_reset_level"],
                int_gear=shared["int_gear"],
                int_gear_after_reset=shared["int_gear_after_reset"],
                mp_wash_end=self._int(self.sim_mp_wash_end, "MP wash 結束等級"),
                quest_equip_hp=shared["quest_equip_hp"],
                hp_mode=shared["hp_mode"],
                auto_method2=bool(self.sim_auto_method2.get()),
                mw_percent=shared["mw_percent"],
                mw_from_level=shared["mw_from_level"],
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
