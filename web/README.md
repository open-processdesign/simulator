# web — Open Process Design front-end

Vite + React + TypeScript + Tailwind CSS v4 + shadcn/ui (themed with `../design/tokens.css`), i18next (EN/TR).

```bash
npm ci
npm run dev      # http://localhost:5173
npm test         # Vitest
npm run build    # type-check + production build to dist/
```

- Design tokens are imported from `design/tokens.css` and exposed to Tailwind in `src/index.css` (`bg-surface`, `text-muted`, `text-accent`, …). Never use raw hex values in components.
- Fonts (Geist, Geist Mono, Source Serif 4; SIL OFL) are self-hosted via Fontsource packages and bundled into `dist/`.
- All user-visible strings live in `locales/en.json` and `locales/tr.json`; a test checks both files have the same keys.
- Workflow step routing uses the URL hash (`#/flowsheet`) so the static build works on GitHub Pages.
- New shadcn/ui components: copy from the shadcn registry into `src/components/ui/` and theme them with tokens (see `components.json`).

## Engine in the browser (T03)

The Python engine (`engine/opd_engine` + MIT `thermo`) runs in a Web Worker on Pyodide (`src/engine/`).
`startEngine()` (`src/engine/client.ts`) boots it and exposes `simulate(doc)`; the worker solves the
flash-drum example once during boot so the first real run is fast.

- Developer page: `engine-test.html` (`npm run dev`, then open `/engine-test.html`).
- Pyodide comes from jsDelivr (version pinned in `src/engine/bootstrap.ts`, must match the `pyodide` npm package);
  `thermo`, `chemicals`, `fluids` come from PyPI via micropip.
- Self-hosting / offline: build with `VITE_PYODIDE_URL=/pyodide/` (absolute URL or root-relative path to an unpacked
  Pyodide release) and `VITE_WHEELS=/wheels/thermo-….whl,…` (comma-separated wheel URLs).
- Load measurement under Node: `PYODIDE_DIST=<unpacked release> WHEEL_DIR=<wheels> npm run spike:engine`.
