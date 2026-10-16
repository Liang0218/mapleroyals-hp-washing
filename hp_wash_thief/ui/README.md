# Desktop UI (CustomTkinter)

Launch:

```bash
pip install -e ".[gui]"
python -m hp_wash_thief.ui
```

Windows exe folder (build on Windows):

```bat
scripts\build_windows.bat
```

The UI only calls `hp_wash_thief.core.api` (`optimize` / `simulate`). It supports
optimization and simulation, optional mid-game resume, HP and MP targets, and
CSV plan export.

Edit INT equipment in the equipment table. The UI previews the available INT by
level and lets you load or save the equipment settings as JSON.

The job selector uses 4th-job names in one field (Thief A–D; other jobs Policy D
only), for example 箭神／神射手 Bowmaster／Marksman. Improve MaxHP follows the
SP schedule in the GUI.
