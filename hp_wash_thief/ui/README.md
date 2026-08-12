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

Job selector covers Thief (A–D) and other classes (Policy D only). Warrior / Brawler
can override Improve MaxHP level; leave blank for automatic SP schedule.
