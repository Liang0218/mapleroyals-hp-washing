"""Equipment management tab for the desktop UI."""

from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from hp_wash_thief.core.equipment import (
    EQUIPMENT_TYPES,
    EquipmentItem,
    compute_int_gear_segments,
    equipment_to_dicts,
    format_int_gear_preview,
    load_equipment,
    parse_equipment,
)
from hp_wash_thief.core.gear import clip_segments_before_reset
from hp_wash_thief.core.models import IntGearSegment
from hp_wash_thief.ui.resources import default_equipment_path
from hp_wash_thief.ui.user_errors import format_user_error


class _EquipmentRow:
    def __init__(self, parent: ctk.CTkScrollableFrame, *, on_change: Callable[[], None]) -> None:
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.grid_columnconfigure(0, weight=3)
        self.frame.grid_columnconfigure(2, weight=1)
        self.frame.grid_columnconfigure(3, weight=1)

        self.name = ctk.CTkEntry(self.frame, placeholder_text="Equipment Name")
        self.name.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.equip_type = ctk.CTkOptionMenu(self.frame, values=list(EQUIPMENT_TYPES))
        self.equip_type.set(EQUIPMENT_TYPES[0])
        self.equip_type.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        self.int_bonus = ctk.CTkEntry(self.frame, width=70, placeholder_text="INT")
        self.int_bonus.grid(row=0, column=2, sticky="ew", padx=(0, 6))

        self.equip_level = ctk.CTkEntry(self.frame, width=70, placeholder_text="Level")
        self.equip_level.grid(row=0, column=3, sticky="ew", padx=(0, 6))

        self.delete_btn = ctk.CTkButton(
            self.frame, text="刪", width=40, command=self._remove
        )
        self.delete_btn.grid(row=0, column=4)

        self._on_change = on_change
        self._parent = parent
        for widget in (self.name, self.int_bonus, self.equip_level):
            widget.bind("<KeyRelease>", lambda _e: on_change())
        self.equip_type.configure(command=lambda _v: on_change())

    def _remove(self) -> None:
        self.frame.destroy()
        self._on_change()

    def set_values(
        self,
        *,
        name: str,
        equip_type: str,
        int_bonus: int,
        equip_level: int,
    ) -> None:
        self.name.delete(0, "end")
        self.name.insert(0, name)
        self.equip_type.set(equip_type)
        self.int_bonus.delete(0, "end")
        self.int_bonus.insert(0, str(int_bonus))
        self.equip_level.delete(0, "end")
        self.equip_level.insert(0, str(equip_level))

    def to_item(self) -> EquipmentItem:
        name = self.name.get().strip()
        equip_type = self.equip_type.get()
        try:
            int_bonus = int(self.int_bonus.get().strip())
            equip_level = int(self.equip_level.get().strip())
        except ValueError as exc:
            raise ValueError(f"「{name or equip_type}」的 INT／穿戴等級必須是整數") from exc
        return EquipmentItem(
            name=name,
            equip_type=equip_type,
            int_bonus=int_bonus,
            equip_level=equip_level,
        )


class EquipmentPanel(ctk.CTkFrame):
    """Editable equipment list with live INT segment preview."""

    def __init__(
        self,
        master,
        *,
        get_int_reset_level: Callable[[], int],
        get_int_gear_after_reset: Callable[[], int],
        max_level: int = 200,
    ) -> None:
        super().__init__(master)
        self._get_int_reset_level = get_int_reset_level
        self._get_int_gear_after_reset = get_int_gear_after_reset
        self._max_level = max_level
        self._rows: list[_EquipmentRow] = []

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self,
            text="裝備管理：每個 Type 僅穿戴一件（Ring 最多 4 件），依等級自動計算 INT 區間",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6))
        for label, cmd, width in (
            ("新增列", self._add_row, 80),
            ("還原預設", self._load_defaults, 90),
            ("載入 JSON…", self._load_json, 100),
            ("儲存 JSON…", self._save_json, 100),
        ):
            ctk.CTkButton(toolbar, text=label, width=width, command=cmd).pack(
                side="left", padx=(0, 6)
            )

        left = ctk.CTkFrame(self)
        left.grid(row=2, column=0, sticky="nsew", padx=(8, 4), pady=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        for col, text, weight in (
            (0, "Equipment Name", 3),
            (1, "Type", 2),
            (2, "INT", 1),
            (3, "Level to Equip", 1),
            (4, "", 0),
        ):
            header.grid_columnconfigure(col, weight=weight if weight else 0)
            ctk.CTkLabel(header, text=text, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=col, sticky="w", padx=(0, 6)
            )

        self._list = ctk.CTkScrollableFrame(left)
        self._list.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self._list.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(self)
        right.grid(row=2, column=1, sticky="nsew", padx=(4, 8), pady=(0, 8))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            right,
            text="智裝 INT 預覽（依等級區間）",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        self.preview = ctk.CTkTextbox(
            right, font=ctk.CTkFont(family="Microsoft JhengHei UI", size=13)
        )
        self.preview.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.status = ctk.CTkLabel(self, text="")
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))

    def load_defaults(self) -> None:
        """Load preset equipment; call after app params are ready."""
        self._load_defaults()

    def _add_row(self, item: Optional[EquipmentItem] = None) -> _EquipmentRow:
        row = _EquipmentRow(self._list, on_change=self._refresh_preview)
        row.frame.grid(row=len(self._rows), column=0, sticky="ew", pady=2)
        self._rows.append(row)
        if item is not None:
            row.set_values(
                name=item.name,
                equip_type=item.equip_type,
                int_bonus=item.int_bonus,
                equip_level=item.equip_level,
            )
        return row

    def _clear_rows(self) -> None:
        for row in self._rows:
            row.frame.destroy()
        self._rows.clear()

    def _collect_items(self) -> list[EquipmentItem]:
        alive: list[_EquipmentRow] = []
        items: list[EquipmentItem] = []
        for row in self._rows:
            if not row.frame.winfo_exists():
                continue
            alive.append(row)
            items.append(row.to_item())
        self._rows = alive
        return items

    def _build_preview_text(self, items: list[EquipmentItem]) -> tuple[str, int, int]:
        reset_level = self._get_int_reset_level()
        after_reset = self._get_int_gear_after_reset()
        pre_reset_cap = max(1, reset_level - 1)
        segments = compute_int_gear_segments(items, max_level=pre_reset_cap)
        clipped = clip_segments_before_reset(segments, int_reset_level=reset_level)
        body = format_int_gear_preview(
            clipped,
            int_reset_level=reset_level,
            int_gear_after_reset=after_reset,
        )
        return body, len(clipped), after_reset

    def current_int_gear_segments(self) -> list[IntGearSegment]:
        """Segments used by optimize/simulate (pre-reset only)."""
        items = self._collect_items()
        reset_level = self._get_int_reset_level()
        pre_reset_cap = max(1, reset_level - 1)
        segments = compute_int_gear_segments(items, max_level=pre_reset_cap)
        return clip_segments_before_reset(segments, int_reset_level=reset_level)

    def _refresh_preview(self) -> None:
        try:
            items = self._collect_items()
            text, seg_count, _after_reset = self._build_preview_text(items)
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", text)
            self.status.configure(text=f"共 {len(items)} 件裝備 · {seg_count} 個等級區間")
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text=f"計算錯誤：{exc}")

    def _load_defaults(self) -> None:
        path = default_equipment_path()
        if path.is_file():
            items = load_equipment(path)
        else:
            items = []
        self._clear_rows()
        for item in items:
            self._add_row(item)
        self._refresh_preview()

    def _load_json(self) -> None:
        path = filedialog.askopenfilename(
            title="載入裝備 JSON",
            filetypes=[("JSON", "*.json"), ("所有檔案", "*.*")],
        )
        if not path:
            return
        try:
            items = load_equipment(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("錯誤", format_user_error(exc))
            return
        self._clear_rows()
        for item in items:
            self._add_row(item)
        self._refresh_preview()

    def _save_json(self) -> None:
        path = filedialog.asksaveasfilename(
            title="儲存裝備 JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            items = self._collect_items()
            parse_equipment(equipment_to_dicts(items))
            Path(path).write_text(
                json.dumps(equipment_to_dicts(items), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            messagebox.showinfo("已儲存", f"已寫入：{path}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("錯誤", str(exc))
