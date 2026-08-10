"""Scrollable result panel: summary text + ttk.Treeview tables."""

from __future__ import annotations

import tkinter.ttk as ttk

import customtkinter as ctk

from hp_wash_thief.core.report import ReportTable

_COL_WIDTHS: dict[str, int] = {
    "#": 36,
    "政策": 48,
    "目標INT": 64,
    "達標等級": 64,
    "洗MP結束等級": 96,
    "總APR": 56,
    "最終HP": 64,
    "達標": 48,
}


class ResultPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self._font = ctk.CTkFont(family="Microsoft JhengHei UI", size=12)
        self._title_font = ctk.CTkFont(family="Microsoft JhengHei UI", size=13, weight="bold")

    def show_text(self, text: str) -> None:
        self.show(text, [], "")

    def show_error(self, message: str, detail: str = "") -> None:
        for child in self.winfo_children():
            child.destroy()

        row = 0
        ctk.CTkLabel(
            self,
            text="錯誤",
            font=self._title_font,
            text_color=("#B00020", "#FF6B6B"),
        ).grid(row=row, column=0, sticky="w", padx=4, pady=(4, 2))
        row += 1

        line_count = message.count("\n") + 1
        box_height = min(200, max(80, line_count * 22))
        box = ctk.CTkTextbox(self, font=self._font, height=box_height)
        box.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 8))
        box.insert("1.0", message)
        box.configure(state="disabled")
        row += 1

        if detail.strip():
            ctk.CTkLabel(
                self,
                text="詳細資訊（除錯用）",
                font=self._title_font,
                text_color=("gray35", "gray65"),
            ).grid(row=row, column=0, sticky="w", padx=4, pady=(4, 2))
            row += 1
            detail_box = ctk.CTkTextbox(self, font=self._font, height=min(240, 80 + detail.count("\n") * 16))
            detail_box.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 8))
            detail_box.insert("1.0", detail)
            detail_box.configure(state="disabled")

    def show(
        self,
        summary: str,
        tables: list[ReportTable],
        footer: str = "",
    ) -> None:
        for child in self.winfo_children():
            child.destroy()

        row = 0
        if summary.strip():
            ctk.CTkLabel(self, text="摘要", font=self._title_font).grid(
                row=row, column=0, sticky="w", padx=4, pady=(4, 2)
            )
            row += 1
            line_count = summary.count("\n") + 1
            box_height = min(260, max(120, line_count * 20))
            box = ctk.CTkTextbox(self, font=self._font, height=box_height)
            box.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 8))
            box.insert("1.0", summary)
            box.configure(state="disabled")
            row += 1

        for table in tables:
            ctk.CTkLabel(self, text=table.title, font=self._title_font).grid(
                row=row, column=0, sticky="w", padx=4, pady=(8, 2)
            )
            row += 1
            self._grid_table(row, table)
            row += 1

        if footer.strip():
            ctk.CTkLabel(
                self,
                text=footer,
                font=self._font,
                text_color=("gray25", "gray75"),
                wraplength=900,
                justify="left",
            ).grid(row=row, column=0, sticky="w", padx=4, pady=(8, 4))

    def _grid_table(self, row: int, table: ReportTable) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=(0, 4))
        frame.grid_columnconfigure(0, weight=1)

        height = min(max(len(table.rows), 1), 10)
        tree = ttk.Treeview(
            frame,
            columns=table.columns,
            show="headings",
            height=height,
        )
        for col in table.columns:
            tree.heading(col, text=col)
            width = _COL_WIDTHS.get(col, 72)
            anchor = "center" if col in ("#", "政策", "達標", "達標等級", "洗MP結束等級") else "e"
            tree.column(col, width=width, anchor=anchor, stretch=(col not in ("#", "政策", "達標")))

        for values in table.rows:
            tree.insert("", "end", values=values)

        tree.grid(row=0, column=0, sticky="ew")
