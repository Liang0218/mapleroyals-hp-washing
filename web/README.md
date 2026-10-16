# MapleRoyals HP Washing Calculator — Web

This directory is the browser-only version of the calculator. It is deliberately
separate from the Python package so the Windows Desktop application, CLI,
PyInstaller specification, and Python test suite continue to work unchanged.

## Local development

Install Node.js 20.19+ or 22.12+. From this directory, install the locked
dependencies and start the development server:

```bash
npm ci
npm run dev
```

Create the static production bundle with:

```bash
npm run build
```

Vite writes the deployable files to `web/dist/`. In Cloudflare Pages, set the
repository root directory to `web`, Build command to `npm run build`, and Build
output directory to `dist`.

Run the browser app tests from this directory with:

```bash
npm test
```

The page includes a guide, job reference, equipment editor with INT preview,
optimizer, simulator, and action reference. Equipment settings can be imported
and exported as JSON; the browser saves equipment and calculator settings in
that browser's local storage. Optimization and simulation support mid-game
resume, HP/MP targets, and CSV plan downloads. Optimization can target levels
31–200 and estimates how the winning plan's HP can continue growing through
level 200.

## Migration status

The browser calculation core includes models, formula helpers, job profiles and
Improve MaxHP tracking, INT gear segments, equipment-slot calculation, policies,
level-by-level simulation, and optimization. Python remains the reference
implementation while cross-language golden fixtures are expanded across jobs
and resume scenarios.
