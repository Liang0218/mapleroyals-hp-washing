"""UI fonts: prefer a CJK family so Roboto does not fall back to decorative fonts."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

# Guide/result textboxes already use this name successfully on Traditional Chinese Windows.
UI_FONT_FAMILY = "Microsoft JhengHei UI"


def apply_ctk_theme_font(family: str = UI_FONT_FAMILY) -> None:
    """Override CustomTkinter's default Roboto for widgets that omit ``font=``."""
    spec = ctk.ThemeManager.theme.get("CTkFont")
    if not isinstance(spec, dict):
        return
    if "family" in spec:
        spec["family"] = family
        return
    for key in ("Windows", "macOS", "Linux"):
        nested = spec.get(key)
        if isinstance(nested, dict) and "family" in nested:
            nested["family"] = family


def apply_tk_named_fonts(root, family: str = UI_FONT_FAMILY) -> None:
    """Align Tk/ttk defaults (messagebox, Treeview) with the same family."""
    from tkinter import font as tkfont
    import tkinter.ttk as ttk

    for name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
    ):
        try:
            tkfont.nametofont(name).configure(family=family)
        except tkfont.TclError:
            continue

    style = ttk.Style(root)
    style.configure("Treeview", font=(family, 10))
    style.configure("Treeview.Heading", font=(family, 10, "bold"))


def ui_font(**kwargs: Any) -> ctk.CTkFont:
    kwargs.setdefault("family", UI_FONT_FAMILY)
    return ctk.CTkFont(**kwargs)
