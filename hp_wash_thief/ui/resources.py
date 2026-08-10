"""Desktop UI helpers (resource paths for PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path


def app_base_dir() -> Path:
    """Return the directory containing bundled resources.

    When frozen by PyInstaller, data files live next to the executable (onedir)
    or under ``sys._MEIPASS`` (onefile). Prefer the executable directory for
    user-editable defaults, falling back to the package/examples location.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    # Repo layout: <root>/hp_wash_thief/ui/resources.py → <root>
    return Path(__file__).resolve().parents[2]


def default_int_gear_path() -> Path:
    base = app_base_dir()
    candidates = [
        base / "examples" / "int_gear.json",
        base / "int_gear.json",
        Path(__file__).resolve().parents[2] / "examples" / "int_gear.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def default_csv_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "plan.csv"
    return Path.cwd() / "plan.csv"
