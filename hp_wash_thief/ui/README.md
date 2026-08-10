# Phase 2 UI (not implemented)

This package reserves `hp_wash_thief.ui` for a future CustomTkinter desktop UI and
PyInstaller Windows packaging.

Phase 1 ships the calculation core + terminal CLI only. The GUI must call
`hp_wash_thief.core.api` (`optimize` / `simulate`) and must not embed wash logic.
