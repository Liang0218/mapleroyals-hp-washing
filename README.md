# MapleRoyals HP Wash APR Optimizer

Reusable Python calculation core + terminal CLI + CustomTkinter desktop GUI for
MapleRoyals HP washing APR optimization (Thief A–D comparison; other jobs Policy D /
Method2). Windows users can build a shareable `.exe` folder with PyInstaller.

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

- Choose **job** (Thief / Bowman / Gunslinger / Brawler / Fighter / Page / Spearman / Beginner)
- Edit **all CLI parameters** (target HP, INT reset level, MW %, policies, Improve MaxHP override, …)
- Edit / load / save **INT gear JSON** in a text box
- Choose a **CSV output path**
- Run **Optimize** or **Simulate** and read the report in-app

Non-Thief jobs hide A–D comparison and search Policy D only (stack INT → MP wash → Method2).

### Build a Windows app folder (on a Windows PC)

```bat
scripts\build_windows.bat
```

Output: `dist\MapleRoyalsHpWash\MapleRoyalsHpWash.exe`  
Zip the whole `MapleRoyalsHpWash` folder and share it (keep DLLs next to the exe).

> CI builds on tag push — see **Releases** below. Local build still works with the script above.

### Download Windows build (GitHub Releases)

Official Windows builds are attached to [GitHub Releases](https://github.com/Liang0218/mapleroyals-hp-washing/releases).

1. Download `MapleRoyalsHpWash-vX.Y.Z-win64.zip`
2. Extract the folder
3. Run `MapleRoyalsHpWash.exe` (keep all files in the folder)

**Publish a new release (maintainers):**

```bash
# bump version in pyproject.toml first, then:
git tag v0.3.0
git push origin v0.3.0
```

GitHub Actions (`.github/workflows/release-windows.yml`) runs tests, builds with PyInstaller on `windows-latest`, and uploads the zip to Releases.

Manual CI test without creating a Release: **Actions → Release Windows → Run workflow** (downloads a 14-day artifact).

## CLI quick start

```bash
# Thief (default): compare policies A–D
python -m hp_wash_thief optimize \
  --job thief \
  --target-hp 27000 \
  --int-reset-level 155 \
  --int-gear-file examples/int_gear.json \
  --policies auto \
  --csv plan.csv
```

```bash
# Bowman / Warrior / Pirate: Policy D only
python -m hp_wash_thief optimize \
  --job fighter \
  --target-hp 30000 \
  --int-reset-level 155 \
  --int-gear-file examples/int_gear.json \
  --improved-maxhp-level 10 \
  --csv plan.csv
```

```bash
python -m hp_wash_thief simulate \
  --job thief \
  --policy mp_wash_shortfall \
  --target-base-int 350 \
  --target-hp 27000 \
  --int-reset-level 155 \
  --int-gear-file examples/int_gear.json \
  --mp-wash-end 100
```

### Supported jobs

| `--job` | Notes |
| --- | --- |
| `thief` | Policies A–D (default) |
| `bowman` | D only, Method2 |
| `gunslinger` | D only, Method2; −16 MP/APR |
| `brawler` | D only; Improve MaxHP (2nd job) auto SP |
| `fighter` / `page` / `spearman` | D only; Improved MaxHP Increase (1st job) |
| `beginner` | D only; no job-advance HP/MP/AP |

**Magician** is not implemented yet.

Optional `--target-mp`: minimum **base MP** at level 200. Omit to wash Extra MP down near job `min_mp` (legacy). Values below `min_mp(200)` for the job are rejected. Optimizer treats HP+MP as joint `reached_target`.

Warrior / Brawler: leave `--improved-maxhp-level` unset to auto-max Improve MaxHP from the SP schedule (no SP-reset alternate wash). Override `0–10` when resuming mid-game.

### Mid-game resume（中途接續）

已經洗到一半時，可提供目前等級與數值，從**本等剩餘 AP**起算後面最省 APR：

```bash
python -m hp_wash_thief optimize \
  --target-hp 27000 \
  --int-reset-level 155 \
  --int-gear-file examples/int_gear.json \
  --from-level 80 \
  --base-hp 12000 \
  --extra-mp 600 \
  --base-int 280 \
  --base-luk 40 \
  --fresh-ap 5 \
  --csv remaining.csv
```

- 語意：角色**已升到**該等（HP/MP 已含自然／職轉加成），本等 AP **尚未**分配。
- 可填 `--base-mp` 或 `--extra-mp`（Extra MP = base MP − min MP）。
- 70／120 剛轉職且職轉 AP 未花時，將 `--fresh-ap` 設為 `10`。
- 報告中的 APR 為**接續後剩餘**（不含過去已花的 wash APR）。
- GUI：Optimize／Simulate 分頁勾選「中途接續」即可。

## What it answers

Given INT gear segments, `int_reset_level`, and `target_hp`:

1. Best (lowest APR) `target_base_int` + phase params — Thief: **Policy A–D**; other jobs: **D only**
2. Cross-policy comparison (Thief): which total APR is lower, by how much, and final HP
3. Global winner with full per-level plan (CSV: `HP5` / `MP5` / `INT5` / `M2` / `RESET_INT` / `STR5` / `DEX5`)

## Policies (early phase until `target_base_int`)

### A / B (from level 31) — Thief

Early phase lasts **until `target_base_int` is reached** (not a fixed level).

| Extra MP vs threshold (fixed **60** = 12×5) | Policy A `mp_wash_shortfall` | Policy B `int_dump_shortfall` |
| --- | --- | --- |
| `>= 60` | HP wash ×5 (Method 1) | HP wash ×5 (Method 1) |
| `< 60` | MP wash ×5 (5 APR) | 5 fresh AP → INT (0 wash APR that level) |

### C — hardcore A (`mp_wash_hardcore`, from level 10) — Thief

Until `target_base_int` is reached, **each fresh AP slot** (5 per level, +5 at job advance):

| Step | Condition | Action |
| --- | --- | --- |
| 1 | Extra MP ≥ 12 | **HP1** (Method 1), then re-check next AP |
| 2 | Still &lt; 12, level ≥ 30 | **MP1**, then re-check |
| 3 | Cannot wash | Remaining AP → INT/LUK (0 APR) |

Levels 10–29 skip step 2 (MP wash not allowed). Levels 2–9 still use BUILD (DEX/INT).

After target INT: same as A/B (dense MP wash → late HP wash → Method 2 → INT reset).

Optimizer searches `target_base_int` + `mp_wash_end`; threshold fixed at 60 for A/B.

### D — plain INT (`int_only_plain`) — all jobs

Stack INT until `target_base_int`, then MP wash / Method2. Non-Thief jobs use this path only (prefer Method2 + primary-stat dump after INT target).

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
from hp_wash_thief.core.jobs import JobId
```

- `optimize(OptimizeConfig) -> OptimizeResult`
- `simulate(SimulateConfig) -> SimulateResult`

Set `OptimizeConfig.job` / `SimulateConfig.job` (default `"thief"`). All formulas / simulation / optimization live under `hp_wash_thief/core/`. CLI and GUI only call this API.

## Layout

```
hp_wash_thief/
  core/          # formulas, jobs, simulator, optimizer, api
  cli.py
  ui/            # CustomTkinter desktop app
examples/
scripts/build_windows.bat
hp_wash_thief.spec
```

## Formula sources

- [Night Lord / Shadower HP Washing Above 20k HP (PerfectSin)](https://royals.ms/forum/threads/night-lord-shadower-hp-washing-above-20k-hp.146816/)
- [HP Washing For New Players](https://royals.ms/forum/threads/hp-washing-for-new-players.41129/)
- [Fully revised HP washing guide](https://royals.ms/forum/threads/fully-revised-hp-washing-guide.8286/)
- [MapleRoyals Skill Library](https://royals.ms/forum/threads/mapleroyals-skill-library.209540/)

### Maple Warrior (important)

Level-up MP uses **total INT** = `base_int + int_gear + floor(base_int * mw_percent)`.

Default: `--mw-percent 0.10 --mw-from-level 10` (10% of **base** INT from level 10 onward).

MP wash still uses **base INT only** (gear/MW do not apply). Maple Warrior is applied via `--mw-percent` / `--mw-from-level`.

### Job advancement AP

Per [MapleRoyals forum #45500](https://royals.ms/forum/threads/2nd-3rd-4th-job-bonuses.45500/): 1st/2nd job grant **0** bonus AP; 3rd/4th job grant **+5** AP each (levels 70 and 120). The simulator adds these on top of the normal 5 AP per level. Beginner has no job advances.

## Tests

```bash
pytest -q
```

## Out of scope

- Web / Streamlit / Electron
- Magician wash (deferred)
- NX market prices, auto-search of `int_reset_level`
- SP-reset alternate Improve MaxHP washing
