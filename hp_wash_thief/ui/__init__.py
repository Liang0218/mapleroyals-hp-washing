"""Desktop UI package (CustomTkinter + PyInstaller).

Import ``hp_wash_thief.ui.app`` only when launching the GUI so core/CLI users
do not need tkinter installed.
"""

__all__ = ["main", "run_app"]


def run_app() -> None:
    from hp_wash_thief.ui.app import run_app as _run

    _run()


def main() -> int:
    from hp_wash_thief.ui.app import main as _main

    return _main()
