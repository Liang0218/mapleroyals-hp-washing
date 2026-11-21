---
name: MapleRoyals HP Washing APR Optimizer
description: A field-guide specimen sheet for HP washing plans; the result is a label you read at a glance.
colors:
  mount: "#e9ede4"
  sheet: "#e9ede4"
  label: "#ffffff"
  well: "#dfe5d8"
  ink: "#1f2a22"
  ink-2: "#455548"
  ink-3: "#5b6b5e"
  rule: "#b9c4b2"
  rule-strong: "#8e9d87"
  bar: "#1f2a22"
  bar-ink: "#e9ede4"
  bar-ink-2: "#b8c4b4"
  bar-rule: "#3a4a3e"
  crimson: "#c2381f"
  crimson-text: "#b8341c"
  crimson-hover: "#a92e17"
  on-crimson: "#ffffff"
  maple: "#f08a5d"
  ochre: "#d98a1c"
  on-ochre: "#1f2a22"
  ochre-tint: "#fbf0d9"
  ochre-ink: "#6b4508"
  moss: "#3f7a3a"
  moss-tint: "#e4efdf"
  danger: "#a8281a"
  danger-tint: "#fbe9e5"
  row-alt: "#f2f5ee"
  row-hover: "#fdf3e2"
  night-mount: "#121815"
  night-sheet: "#182019"
  night-label: "#1d261f"
  night-well: "#263128"
  night-ink: "#e6e9dc"
  night-ink-2: "#b9c2b2"
  night-ink-3: "#9aa596"
  night-rule: "#324034"
  night-rule-strong: "#4a5b4c"
  night-bar: "#0b100d"
  night-crimson: "#e0573a"
  night-crimson-text: "#f4866c"
  night-on-crimson: "#1a0a05"
  night-ochre: "#e2a14a"
  night-ochre-ink: "#f2cf94"
  night-moss: "#85c27a"
  night-danger: "#ff9d8c"
typography:
  display:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 800
    lineHeight: 1.15
    fontFeature: "tnum"
  headline:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "clamp(1.3rem, 2.4vw, 1.75rem)"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "clamp(1.3rem, 2.2vw, 1.55rem)"
    fontWeight: 800
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "0.86rem"
    fontWeight: 600
  table:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    fontFeature: "tnum"
  plate:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    letterSpacing: "-0.01em"
  caption:
    fontFamily: "Archivo, Noto Sans TC, Microsoft JhengHei, system-ui, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 400
rounded:
  none: "0px"
  mark: "50%"
spacing:
  xs: "0.3rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  gutter: "clamp(1rem, 3vw, 2rem)"
components:
  button-primary:
    backgroundColor: "{colors.crimson}"
    textColor: "{colors.on-crimson}"
    rounded: "{rounded.none}"
    padding: "0.5rem 1rem"
    height: "2.5rem"
  button-primary-hover:
    backgroundColor: "{colors.crimson-hover}"
  button-run:
    backgroundColor: "{colors.crimson}"
    textColor: "{colors.on-crimson}"
    rounded: "{rounded.none}"
    height: "3.1rem"
    width: "100%"
  button-quiet:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.5rem 1rem"
  button-quiet-hover:
    backgroundColor: "{colors.well}"
  input:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.45rem 0.6rem"
    height: "2.5rem"
  input-invalid:
    backgroundColor: "{colors.danger-tint}"
  tab:
    textColor: "{colors.bar-ink-2}"
    padding: "0.55rem 1.05rem"
    height: "2.6rem"
  tab-active:
    backgroundColor: "{colors.mount}"
    textColor: "{colors.ink}"
  segmented-active:
    backgroundColor: "{colors.ochre}"
    textColor: "{colors.on-ochre}"
  specimen:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "1.6rem 1.5rem 0"
  specimen-tag:
    backgroundColor: "{colors.ochre}"
    textColor: "{colors.on-ochre}"
    typography: "{typography.caption}"
    padding: "0.1rem 0.6rem"
  mark:
    rounded: "{rounded.mark}"
    size: "0.62em"
  section-plate:
    textColor: "{colors.ink}"
    typography: "{typography.plate}"
  comparison-winner:
    backgroundColor: "{colors.label}"
    textColor: "{colors.ink}"
    padding: "0.8rem 1rem"
  winner-tag:
    backgroundColor: "{colors.ochre}"
    textColor: "{colors.on-ochre}"
    padding: "0 0.45rem"
  table-header:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    padding: "0.5rem 0.65rem"
---

# Design System: MapleRoyals HP Washing APR Optimizer

## Overview

**Creative North Star: "The Field-Guide Specimen Sheet"**

A washing plan is treated as a collected specimen. The page is a herbarium mount board in sage grey-green, structured by ink-green rules; the result is a specimen label pinned to it, read at a glance: a plan code on its tag, the headline line, a printed stamp for reached or missed, the final HP set against its target in words, and a ruled strip of four key figures. Policy behaviour is set as a field guide's dichotomous key numbered in level order, the four policies sit in a ruled comparison strip with the winner outlined, and the level-by-level plan is a plain ruled table under its own section plate. The dark appearance is the same cabinet at night: moss-black ground, bone text, the same crimson and ochre, lifted for contrast.

Density is that of a working reference sheet: compact tables, tabular figures everywhere numbers live, labels small and semibold, headings heavy. Everything is square and flat; depth comes from ground layers and 1px rules, never from shadow. Archivo sets every Latin glyph and figure; CJK deliberately uses the system Traditional Chinese face rather than a shipped CJK font. The world rejects both the generic dark gaming dashboard and the parchment-and-serif game skin.

**Key Characteristics:**
- Paper grounds stacked by tone and outlined by 1px rules: in light the page card shares the mount's tone, so label white is the one raised paper.
- Square corners on every surface; the drawn state mark is the one round form.
- Crimson is the one action; ochre marks the specimen tag, the winner tag, selection, focus and caution; moss marks reached.
- States are drawn printed marks: filled circle reached, hollow circle missed, ochre strike-through when stale.
- Tabular figures on every number.

## Colors

A muted botanical palette: sage paper and ink-green structure, with three saturated field inks used sparingly.

### Primary
- **Maple Crimson** (crimson): the one action colour. Fills every primary button, the full-width run button, and the disclosure marker. `crimson-text` is its text-safe sibling for links, key codes, step numerals and "missed" marks; `crimson-hover` is the pressed/hover fill.

### Secondary
- **Specimen Ochre** (ochre): the specimen tag, the winner tag in the policy comparison, the active segmented switch, text selection, the focus outline, and the strike-through on stale results. `ochre-tint` with `ochre-ink` is the caution notice and the undo bar.

### Tertiary
- **Reached Moss** (moss): the "reached" stamp, success status in comparisons, code in the strategy guide. `moss-tint` grounds the tip notice.

### Neutral
- **Mount Board** (mount): page ground and the active tab, so the tab reads as cut into the board.
- **Sheet** (sheet): the page card and the sticky run bar; secondary strips inside the specimen. In light it carries the mount's own value, so the page card is drawn by its rule alone; at night it lifts one step above the mount.
- **Label White** (label): the highest paper: form sections, specimen label, tables, key, disclosures, inputs.
- **Well** (well): table header ground, quiet-button hover.
- **Ink Green** (ink / ink-2 / ink-3): primary text, secondary text, hints and captions. `ink` also draws the strong rules (specimen border, winner outline, section-plate rules, table header underline, list tops).
- **Rule / Rule Strong** (rule, rule-strong): hairline dividers and input borders respectively.
- **Ink-Green Bar** (bar, bar-ink, bar-ink-2, bar-rule): the app bar and its text, inactive tab text and switch outlines.
- **Maple Orange** (maple): only the "MapleRoyals" word in the product name.
- **Danger** (danger, danger-tint): invalid fields and the error box.
- **Row Alt / Row Hover** (row-alt, row-hover): zebra and hover rows in tables.

Dark values live under the `night-` keys and are applied through `prefers-color-scheme: dark` (unless `data-theme="light"`) and `[data-theme="dark"]`; every role keeps its name, only the value changes.

### Named Rules
**The One Action Rule.** Crimson fills only things you press to act. Never use it as a decorative accent or a heading colour beyond `crimson-text` marks.

**The Three Inks Rule.** Saturated colour comes only from crimson, ochre and moss, each with a fixed meaning (act, mark/caution, reached). Add a new hue only with a new meaning.

## Typography

**Display Font:** Archivo (variable 100-900, self-hosted, Latin and Latin Extended only)
**Body Font:** Archivo, same stack
**CJK:** the system Traditional Chinese face through the stack's fallbacks (Noto Sans TC where installed, Microsoft JhengHei), never a shipped CJK webfont
**Label/Mono Font:** ui-monospace, Consolas for `code` only

**Character:** A single grotesque at two weights does all the work: heavy 800 for anything you read first, 400-600 for everything else. It reads like a printed survey label rather than a game UI.

### Hierarchy
- **Display** (800, 1.75rem, 1.15): the four specimen figures; tabular numerals.
- **Headline** (800, clamp(1.3rem, 2.4vw, 1.75rem), 1.2): the specimen headline line.
- **Title** (800, clamp(1.3rem, 2.2vw, 1.55rem)): page headings. The app-bar product name is clamp(1.15rem, 2.4vw, 1.5rem) at 800.
- **Plate** (800, 1.25rem; 1.1rem inside the key): result section headings (key, policy comparison, plan table), each set under a 1px ink rule like a plate heading in a field guide.
- **Body** (400, 1rem, 1.55): prose, notices, subheadings capped at 70ch.
- **Label** (600, 0.86rem): form labels, switch text; hints at 0.8rem/500.
- **Table** (400, 0.85rem, tabular): plan and reference tables; headers at 800.
- **Caption** (0.78-0.84rem): figure terms, runbar note, footer, specimen tag and winner tag (800).

### Named Rules
**The Tabular Rule.** Every number is set with tabular figures (inputs, tables, figures, captions) so columns align across rows and reruns.

**The Two-Weight Rule.** 800 for headings, figures, table headers, buttons and active tabs; 600 and below for the rest. No intermediate display weights.

## Layout

A centred shell at max 1440px with a fluid gutter (clamp(1rem, 3vw, 2rem)), shared by the app bar and the content. The app bar is a full-bleed ink-green band (min 64px row) with the product name left and the language and appearance switches right; tabs hang from its bottom edge with 2px gaps and scroll horizontally when crowded.

The Optimize and Simulate tabs use a two-column grid: a form column (max 420px) and a results column, gap 1.2rem by 1.6rem. The specimen label and the key are grouped as the result lead and occupy the results column beside the form (gap 1.2rem); the policy comparison and plan table follow below, spanning both columns. The run button lives in a sticky bar at the bottom of the form column. At 1100px and below the grid collapses to one column; at 720px the app bar stacks, the figure strip drops from four columns to two, and side panels unstick.

Rhythm is rem-based: 0.3rem inside labels, 0.5rem and 1rem for gaps and padding, 1.5rem between shell regions. Tables scroll inside their frame (max-height 560px) with sticky headers.

## Elevation & Depth

Flat. There are no shadows anywhere. Depth is tonal and ruled: mount board underneath, sheet for page cards (the same tone as the mount in light, a step up at night), label white for the things you read or edit, each outlined with a 1px rule. A 2px ink line marks the chosen thing: the specimen label's border, which makes it the first thing read, and the inset outline on the winning policy.

### Named Rules
**The Paper Stack Rule.** Raise an element by moving it up the ground stack (mount, sheet, label) and giving it a rule, never with a shadow.

**The Chosen Line Rule.** 2px ink is reserved for the answer: the specimen label and the winning comparison cell. Everything else takes 1px.

## Shapes

Every surface corner is square (0 radius), including buttons, inputs, tabs, switches, notices and tables. The one round form is the drawn state mark, a small circle (0.62em, 2px currentColor ring) filled when reached and hollow when missed, used in the stamp and the comparison status. Lines carry the form language: solid 1px rules for structure, solid ink for the strongest divisions and section plates, dashed rules between specimen figures and for secondary separations, dotted rules between key rows. The single tilted form is the stamp, rotated -2deg like a rubber stamp on a label.

## Components

### Buttons
Square and inked; crimson is the one action.
- **Shape:** square corners (0), min height 2.5rem, 1px border in the fill colour.
- **Primary:** crimson fill, on-crimson text, weight 800, padding 0.5rem 1rem.
- **Hover / Focus:** fill and border shift to crimson-hover over 0.15s ease-out; focus is a 2px ochre outline offset 2px. Disabled drops to 0.75 opacity with a progress cursor.
- **Run:** the primary button at full width, 3.1rem tall, 1.1rem text; while busy it pulses opacity (1.2s, alternate).
- **Quiet:** label-white fill, ink text, rule-strong border; hover moves to well with an ink-3 border.
- **Remove:** transparent with danger text; hover takes the danger tint and border.

### Segmented switches
- **Style:** inline group outlined in bar-rule on the app bar; transparent buttons in bar-ink-2 at 0.86rem/600.
- **State:** the pressed option fills ochre with on-ochre text; hover on others lifts to bar-rule.

### Cards / Containers
- **Corner Style:** square.
- **Background:** page cards on sheet; form sections, disclosures, key, tables and previews on label.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px rule.
- **Internal Padding:** 1rem for sections, clamp(1rem, 2.2vw, 1.6rem) for page cards.
- **Notices:** borderless tinted blocks: moss-tint with a moss title for tips, ochre-tint with ochre-ink for caution.

### Inputs / Fields
- **Style:** label-white ground, 1px rule-strong border, square, min height 2.5rem, tabular figures. Labels stack above the field at 0.86rem/600 in ink-2, hints below in ink-3.
- **Focus:** 2px ochre outline at 0 offset plus an ink border.
- **Error:** 2px danger border on danger-tint ground; the error box repeats that treatment at block scale.

### Navigation
- **Tabs:** text buttons hanging from the ink-green bar in bar-ink-2, weight 600. Hover lifts the ground to bar-rule. The active tab takes the mount ground, ink text and weight 800 so it reads as cut into the board below.

### Specimen Label (signature)
The result. A label-white panel with a 2px ink border. An ochre tag sits across its top edge (caption size, 800) and carries the plan code, "No." followed by policy letter, base INT and MP wash end level joined by middots (for example "No. C·360·108"): an identifier, not a category heading. The headline line (headline type, tabular) shares a row with the stamp: a 2px currentColor border box rotated -2deg, moss when reached, crimson-text when missed, led by the drawn mark. Below, one line states the final HP against its target in words (title weight, tabular): "最終 HP 27,010／目標 27,000（多 10）", the margin in ink-2, or "HP 差 N" in danger at 800 when short. Most plans reach their target, so a bar would sit near full and carry no information; the stamp already says reached or missed. The MP caption follows, then a full-bleed strip of four figures divided by dashed rules, each figure in display type with its term underneath in caption ink-3. Optional extras sit in a sheet strip below. When inputs change after a run, the headline and figures are struck through in 2px ochre with an ochre-ink stale note. The panel enters with a 0.3s rise (cubic-bezier(.16, 1, .3, 1)).

### Dichotomous Key (signature)
A label-white panel under a plate heading, listing the plan's steps as a key in level order: crimson-text key code column (800), action, level range, APR right-aligned, rows separated by dotted rule-strong lines. Steps are numbered 1, 2, 3 by first level; steps whose level ranges overlap are either/or alternatives and share a number as a/b (2a, 2b).

### Policy Comparison
A ruled strip of label-white cells, one per policy, divided by 1px rules: policy letter with a moss or crimson-text status led by the drawn mark, total APR at 1.2rem/800 tabular, details in ink-2. The winning cell takes a 2px ink inset outline and a small ochre "優勝" tag (0.78rem/800) at its top left.

### Plan Tables
Ruled tables under a plate heading with the CSV action at its right, inside a scrolling frame: sticky headers on well with an ink underline, 1px rule rows, row-alt zebra and ochre-warm row-hover, numbers right-aligned in tabular figures, action names in the interface language.

## Do's and Don'ts

### Do:
- **Do** keep every surface corner square (0) and every container flat, separated by 1px rules.
- **Do** reserve crimson for the action and its outcome; mark everything else with ochre, moss or ink.
- **Do** set every number in tabular figures.
- **Do** show state as a drawn mark (a CSS circle, never a text glyph): filled for reached, hollow for missed, ochre strike-through for stale.
- **Do** head each result section with a plate: 1.25rem/800 under a 1px ink rule.
- **Do** report a measure against its target as numbers in words (final, target, margin or shortfall); don't draw a bar that sits near full for nearly every result.
- **Do** define every colour as a role token and give it a night value under both the media query and `[data-theme="dark"]`.
- **Do** use the 2px ochre outline for focus everywhere.

### Don't:
- **Don't** add box-shadows or rounded corners to surfaces; depth is the paper stack, and the state mark is the only round form.
- **Don't** ship a CJK webfont; Chinese text uses the system Traditional Chinese face.
- **Don't** introduce a second typeface for display; Archivo at 800 is the display voice.
- **Don't** reskin toward a dark gaming dashboard or a parchment-and-serif game look.
- **Don't** use maple orange anywhere but the product name.
