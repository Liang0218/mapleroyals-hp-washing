# MapleRoyals Thief HP Wash APR Optimizer

Reusable Python calculation core + terminal CLI + CustomTkinter desktop GUI for
MapleRoyals Thief (Night Lord / Shadower) HP washing APR optimization with dual
shortfall-policy comparison. Windows users can build a shareable `.exe` folder
with PyInstaller.

## Requirements

- Python 3.11+
- Core/CLI: no runtime dependencies
- GUI: `customtkinter` (`pip install -e ".[gui]"`)
- Windows exe build: `pip install -e ".[build]"` then run `scripts/build_windows.bat`

## Install

```bash
pip install -e ".[dev,gui]"
```

## Desktop GUI (recommended for Windows friends)

```bash
python -m hp_wash_thief.ui
# or
hp-wash-thief-gui
```

In the window you can:

- Edit **all CLI parameters** (target HP, INT reset level, MW %, policies, …)
- Edit / load / save **INT gear JSON** in a text box
- Choose a **CSV output path**
- Run **Optimize** or **Simulate** and read the report in-app

### Build a Windows app folder (on a Windows PC)

```bat
scripts\build_windows.bat
```

Output: `dist\MapleRoyalsHpWash\MapleRoyalsHpWash.exe`  
Zip the whole `MapleRoyalsHpWash` folder and share it (keep DLLs next to the exe).

> This cloud/Linux environment cannot produce a Windows `.exe`; build on Windows (or a Windows CI runner).

## CLI quick start

```bash
python -m hp_wash_thief optimize \
  --target-hp 27000 \
  --int-reset-level 155 \
  --int-gear-file examples/int_gear.json \
  --policies both \
  --csv plan.csv
```

```bash
python -m hp_wash_thief simulate \
  --policy mp_wash_shortfall \
  --target-base-int 350 \
  --target-hp 27000 \
  --int-reset-level 155 \
  --int-gear-file examples/int_gear.json \
  --mp-wash-end 100
```

## What it answers

Given INT gear segments, `int_reset_level`, and `target_hp`:

1. Best (lowest APR) `target_base_int` + phase params for **Policy A** and **Policy B**
2. Cross-policy comparison: which total APR is lower, by how much, and final HP
3. Global winner with full per-level plan (CSV: `HP5` / `MP5` / `INT5` / `M2` / `RESET_INT`)

## Policies (post-30 early phase)

Early phase lasts **until `target_base_int` is reached** (not a fixed level).

| Extra MP vs threshold (fixed **60** = 12×5) | Policy A `mp_wash_shortfall` | Policy B `int_dump_shortfall` |
| --- | --- | --- |
| `>= 60` | HP wash ×5 (Method 1) | HP wash ×5 (Method 1) |
| `< 60` | MP wash ×5 (5 APR) | 5 fresh AP → INT (0 wash APR that level) |

After target INT: dense MP wash until `mp_wash_end`, then late Method 1 HP wash, Method 2 top-up, INT→LUK at `int_reset_level`.

Optimizer searches `target_base_int` + `mp_wash_end` only (threshold fixed at 60).

## APR cost

```
total_apr =
  mp_wash_count
  + method1_hp_wash_count
  + method2_hp_wash_count
  + int_reset_apr   # base_int_peak - 4
```

Policy B’s INT dump does not spend wash APR on shortfall levels, but increases later `int_reset_apr`; the optimizer accounts for that.

## Core API

```python
from hp_wash_thief.core.api import optimize, simulate
```

- `optimize(OptimizeConfig) -> OptimizeResult`
- `simulate(SimulateConfig) -> SimulateResult`

All formulas / simulation / optimization live under `hp_wash_thief/core/`. CLI and GUI only call this API.

## Layout

```
hp_wash_thief/
  core/          # formulas, simulator, optimizer, api
  cli.py
  ui/            # CustomTkinter desktop app
examples/
scripts/build_windows.bat
hp_wash_thief.spec
```

## Formula sources

- [Night Lord / Shadower HP Washing Above 20k HP (PerfectSin)](https://royals.ms/forum/threads/night-lord-shadower-hp-washing-above-20k-hp.146816/)
- [HP Washing For New Players](https://royals.ms/forum/threads/hp-washing-for-new-players.41129/)

### Maple Warrior (important)

Level-up MP uses **total INT** = `base_int + int_gear + floor(base_int * mw_percent)`.

Default: `--mw-percent 0.10 --mw-from-level 10` (10% of **base** INT from level 10 onward).

MP wash still uses **base INT only** (gear/MW do not apply). Maple Warrior is applied via `--mw-percent` / `--mw-from-level`.

### Job advancement AP

Per [MapleRoyals forum #45500](https://royals.ms/forum/threads/2nd-3rd-4th-job-bonuses.45500/): 1st/2nd job grant **0** bonus AP; 3rd/4th job grant **+5** AP each (levels 70 and 120). The simulator adds these on top of the normal 5 AP per level.

## Tests

```bash
pytest -q
```

## Out of scope

- Web / Streamlit / Electron
- Other classes, NX market prices, auto-search of `int_reset_level`
- Additional hybrid shortfall variants beyond A/B
