"""UI font helpers (CustomTkinter theme family)."""

from __future__ import annotations

import pytest

pytest.importorskip("customtkinter")

import customtkinter as ctk  # noqa: E402

from hp_wash_thief.ui.fonts import UI_FONT_FAMILY, apply_ctk_theme_font  # noqa: E402


def test_apply_ctk_theme_font_overrides_family():
    ctk.set_default_color_theme("green")
    apply_ctk_theme_font()
    spec = ctk.ThemeManager.theme["CTkFont"]
    assert spec["family"] == UI_FONT_FAMILY


def test_apply_ctk_theme_font_nested_platform_dict():
    original = ctk.ThemeManager.theme.get("CTkFont")
    ctk.ThemeManager.theme["CTkFont"] = {
        "Windows": {"family": "Roboto", "size": 13, "weight": "normal"},
        "macOS": {"family": "SF Display", "size": 13, "weight": "normal"},
        "Linux": {"family": "Roboto", "size": 13, "weight": "normal"},
    }
    try:
        apply_ctk_theme_font()
        for key in ("Windows", "macOS", "Linux"):
            assert ctk.ThemeManager.theme["CTkFont"][key]["family"] == UI_FONT_FAMILY
    finally:
        ctk.ThemeManager.theme["CTkFont"] = original
