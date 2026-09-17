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

The UI only calls `hp_wash_thief.core.api` (`optimize` / `simulate`).

Job selector uses 4th-job names in one field (Thief A–D; others Policy D only),
e.g. 箭神／神射手 Bowmaster／Marksman. Improve MaxHP always follows the SP
schedule in the GUI.
