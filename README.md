# MapleRoyals Thief HP Wash APR Optimizer

Phase 1: reusable Python calculation core + terminal CLI for MapleRoyals Thief
(Night Lord / Shadower) HP washing APR optimization with dual shortfall-policy comparison.

Phase 2 (not implemented): CustomTkinter desktop UI + PyInstaller Windows exe.
The `hp_wash_thief/ui/` package is reserved; UI must call `hp_wash_thief.core.api` only.

## Requirements

- Python 3.11+
- No runtime dependencies (pytest optional for tests)

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```bash
python -m hp_wash_thief optimize \
  --target-hp 28000 \
  --int-reset-level 140 \
  --int-gear-file examples/int_gear.json \
  --policies both \
  --csv plan.csv
```

```bash
python -m hp_wash_thief simulate \
  --policy mp_wash_shortfall \
  --target-base-int 400 \
  --target-hp 30000 \
  --int-reset-level 145 \
  --int-gear-file examples/int_gear.json \
  --early-phase-end 70 \
  --mp-wash-end 145 \
  --extra-mp-threshold 60
```

## What it answers

Given INT gear segments, `int_reset_level`, and `target_hp`:

1. Best (lowest APR) `target_base_int` + phase params for **Policy A** and **Policy B**
2. Cross-policy comparison: which total APR is lower, by how much, and final HP
3. Global winner with full per-level plan (CSV: `HP5` / `MP5` / `INT5` / `M2` / `RESET_INT`)

## Policies (post-30 early phase)

| Extra MP vs threshold (default 60) | Policy A `mp_wash_shortfall` | Policy B `int_dump_shortfall` |
| --- | --- | --- |
| `>= threshold` | HP wash ×5 (Method 1) | HP wash ×5 (Method 1) |
| `< threshold` | MP wash ×5 (5 APR) | 5 fresh AP → INT (0 wash APR that level) |

Later phases (dense MP wash window, late Method 1 HP wash, Method 2 top-up, INT→LUK reset) share the same parameter framework.

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

All formulas / simulation / optimization live under `hp_wash_thief/core/`. CLI (and future GUI) only call this API.

## Layout

```
hp_wash_thief/
  core/
    formulas.py
    models.py
    gear.py
    policy/
    simulator.py
    optimizer.py
    report.py
    api.py
  cli.py
  ui/          # Phase 2 placeholder
tests/
examples/int_gear.json
```

## Formula sources

- [Night Lord / Shadower HP Washing Above 20k HP (PerfectSin)](https://royals.ms/forum/threads/night-lord-shadower-hp-washing-above-20k-hp.146816/)
- [HP Washing For New Players](https://royals.ms/forum/threads/hp-washing-for-new-players.41129/)

### Maple Warrior (important)

Level-up MP uses **total INT** = `base_int + int_gear + floor(base_int * mw_percent)`.

Default: `--mw-percent 0.10 --mw-from-level 10` (10% of **base** INT from level 10 onward).

MP wash still uses **base INT only** (gear/MW do not apply). Do not put MW into the gear JSON `mw_int` field as a flat constant — that field is only an optional flat add-on.

## Tests

```bash
pytest -q
```

## Intentionally out of scope (Phase 1)

- CustomTkinter / exe packaging
- Web / Streamlit / Electron
- Other classes, NX market prices, auto-search of `int_reset_level`
- Additional hybrid shortfall variants beyond A/B
