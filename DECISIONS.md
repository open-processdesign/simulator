# DECISIONS

Format: ID · date · decision · why · status. Superseded decisions stay, marked `superseded by Dxxx`.

**D001 · 2026-11-13 · License: GPL-3.0 for code; CC BY 4.0 (planned) for data contributions.**
Compatible with DWSIM (GPL). Core stays open and free forever. — accepted

**D002 · 2026-11-13 · DWSIM is reached only through an engine adapter, as a separate service.**
Limits dependency on DWSIM (single main maintainer; main GitHub repo archived Aug 2026) and keeps a clean GPL boundary. Pin the DWSIM version; keep a copy of the source used. — accepted

**D003 · 2026-11-13 · Own engine-independent data format ("OPD flowsheet", JSON, `schema/flowsheet.schema.json`).**
Data, templates and libraries survive engine changes. Never store DWSIM files as the source of truth. — accepted

**D004 · 2026-11-13 · Strangler-fig replacement of the engine.**
Order: thermodynamics → simple units → reactors → columns. A new module runs in shadow mode next to DWSIM; switched on by a human only when |x_new − x_ref|/|x_ref| < ε on tests and real use. DWSIM stays as fallback. — accepted

**D005 · 2026-11-13 · Second adapter "reference" built on MIT-licensed `thermo`/`chemicals`.**
Gives tests and local development without DWSIM, de-risks the December demo if headless DWSIM is late, and is the seed of own modules. — accepted

**D006 · 2026-11-13 · Stack.**
Front-end: React + TypeScript + Vite, Tailwind CSS, shadcn/ui, React Flow (`@xyflow/react`), i18next.
Back-end: Python 3.12, FastAPI, Pydantic v2. Tests: Vitest, pytest. CI: GitHub Actions.
Why: widest contributor pool, all permissive/compatible licenses, scientific Python ecosystem next to the engine layer. — accepted

**D007 · 2026-11-13 · Internal units are SI** (K, Pa, mol/s, J/mol, mole fractions). Unit sets are a UI concern only. — accepted

**D008 · 2026-11-13 · Design system** (see `docs/DESIGN_SYSTEM.md`): warm light background, soft black text (#1F1D1A), single orange accent (#D9733B); fonts Geist (UI), Geist Mono (numbers), Source Serif 4 (headings), all SIL OFL. Colour only where it carries meaning. — accepted

**D009 · 2026-11-13 · Languages: English default, Turkish second.** All strings via `web/locales/*.json`; docs and code in English. — accepted

**D010 · 2026-11-13 · Agent workflow.** One developer agent, 3 nights/week, one task per night, lock rule with `[WIP]` draft PRs, protected `main`. Communication only through the repo. — accepted
