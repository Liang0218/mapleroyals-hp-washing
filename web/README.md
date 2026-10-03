# MapleRoyals HP Washing Calculator — Web

This directory is the browser-only version of the calculator. It is deliberately
separate from the Python package so the Windows Desktop application, CLI,
PyInstaller specification, and Python test suite continue to work unchanged.

## Local development

Install Node.js 20.19+ or 22.12+, then run:

```bash
npm install
npm run dev
```

Create the static production bundle with:

```bash
npm run build
```

Vite writes the deployable files to `web/dist/`. In Cloudflare Pages, set the
repository root directory to `web`, Build command to `npm run build`, and Build
output directory to `dist`.

## Migration status

The calculation core includes models, formula helpers, job profiles and Improve
MaxHP tracking, INT gear segments, equipment-slot calculation, policies,
level-by-level simulation, and optimization. The page currently provides
simulation, optimization, JSON import/export, and CSV plan download. Python
remains the source of truth until more cross-language golden fixtures cover
each supported job and resume scenario.
