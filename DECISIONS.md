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

**D011 · 2026-11-20 · No server for the December demo; the engine runs in the browser.**
The team is the maintainer + Claude; no server is available. The demo uses the `reference` adapter (MIT `thermo`) running in the browser via Pyodide, and is hosted for free on GitHub Pages. Own modules (recycle solver, shortcut column, …) are written from textbooks. Supersedes the M1 plan of DWSIM as the demo engine. — accepted (pending T03 spike)

**D012 · 2026-11-20 · DWSIM moves after the demo.**
DWSIM needs a server. Options, in order: free container hosting tier; a cheap small VPS; a sponsor/university server once the demo exists. The adapter interface (D002) keeps this a drop-in change. If T03 shows Pyodide is not viable, the same free container host runs the FastAPI + reference engine. — accepted

**D013 · 2026-11-21 · Reference adapter conventions (T04).**
Ports: feed `out`; product `in`; mixer `in*` → `out`; splitter `in` → any outlets; heater/valve `in` → `out`; flash `in` → `vapor`, `liquid`. Specs: heater one of temperature / duty / vapor_fraction (+ optional pressure or pressure_drop); valve pressure or pressure_drop (isenthalpic); flash pressure or pressure_drop + one of temperature / duty / vapor_fraction; splitter `split_<port>` fractions for all outlets but one; mixer adiabatic at the lowest inlet pressure unless `pressure` is given. Duty is heat added to the stream (W). Empty streams (flow 0, e.g. the vapour outlet of a subcooled flash) carry T and P only, no composition. Binary k_ij: user/literature values in the document first, then the ChemSep PR table shipped with `thermo`, otherwise 0 with a `missing_binary_parameter` warning. The full table is in the module docstring of `engine/opd_engine/adapters/reference.py`. — accepted

**D014 · 2026-11-21 · Pyodide spike result: the engine runs in the browser (confirms D011).**
`opd_engine` + `thermo` 0.6.1 run unchanged on Pyodide 314.0.8 (CPython 3.14) in a Web Worker; results equal native CPython (flash-drum y_benzene 0.62111 both).
Measured with local files (no network), headless Chrome: Python runtime 2.2 s, numpy/scipy/pandas/pydantic 2.6 s, thermo/chemicals/fluids install 1.7 s, engine import 2.8 s, warm-up solve 3.3 s → ready in ≈ 13 s; then a solve takes ≈ 15–30 ms. Node gives the same picture.
Download on first visit ≈ 67 MB (Pyodide core 13.5, compiled packages 23.9, PyPI wheels 29.3 of which `chemicals` alone is 22 MB); later visits come from the browser cache.
Decisions: (1) keep the in-browser engine for the demo, no server; (2) start loading the engine in the background as soon as the app opens and show progress; (3) a warm-up solve during boot hides `thermo`'s lazy data loading. Follow-ups (not blocking the demo): trim `chemicals` data to the components we offer, self-host wheels on GitHub Pages, Cache Storage for offline use. — accepted

**D015 · 2026-11-21 · Component search uses a static index built from `chemicals`; k_ij sources come from the engine.**
`engine/scripts/build_component_index.py` writes `web/src/data/components.json` (1347 components, 52 kB gzipped): every `chemicals` component with curated critical data (IUPAC, Matthews, CRC, PSRK), acentric factor, normal boiling point and the correlations the reference engine needs. Search is instant and works before the engine has loaded; a test checks index entries load in the engine. The binary-parameter table asks the engine (`runtime.binary_parameters`), so it shows exactly the k_ij the run will use: document value → ChemSep table → 0 ("missing"). The OPD document lives in one reducer (`web/src/state/flowsheet.ts`); the engine starts loading when the app opens (`EngineProvider`). — accepted

**D016 · 2026-11-21 · Flowsheet canvas conventions (T06).**
React Flow (`@xyflow/react` 13, MIT) renders the OPD document; the document stays the only state (reducer actions `add_unit`, `connect`, `set_spec`, …), React Flow only keeps view state (drag, selection, sizes). Unit ids `FEED-1`, `F-1`, `H-1`, … and stream ids `S1`, `S2`, …. Fixed ports per unit type from `web/src/flowsheet/catalog.ts` (mixer 3 inlets, splitter 3 outlets for now); a port takes one stream; outlet → inlet only. Feed conditions are edited on the feed's outgoing stream (as in the OPD example). Spec groups are exclusive choices (e.g. temperature / duty / vapour fraction). Inputs are SI only until unit sets (M2). Status dots come from the engine's `validate` (no calculation), refreshed 250 ms after each edit: grey = not checked, green = inputs complete, amber = missing input, red = error; each dot has a text label. Units the demo engine cannot solve yet are visible in the palette but disabled ("coming later"). — accepted

**D017 · 2026-11-21 · Run and results (T07).**
The Run button (top bar, Run step, Results step) sends the whole OPD document to the engine worker; the last result is kept in `RunProvider` with a fingerprint of the process data (document without `layout`/`results`). Any later edit marks the results stale (banner, canvas phase colours and stream table hidden) instead of silently showing old numbers. After a run: stream table (one column per stream: T, P, flow, vapour fraction, mole fractions), unit result cards, engine messages; each message, stream header and unit links to the canvas through a shared selection. Status dots: hollow green = inputs complete, filled green = solved. Streams coloured by phase after a run (vapour / liquid / two-phase tokens). Canvas selection is driven by click events, not React Flow's selection callback (avoids a feedback loop). — accepted

**D018 · 2026-11-21 · Recycle loops: automatic tear streams + bounded Wegstein (T08).**
The reference engine groups units into strongly connected components (Tarjan) and solves them in topological order. In each loop the tear streams are the back edges of a depth-first search from the loop's entry units (breaks every cycle; Westerberg et al., *Process Flowsheeting*, 1979). Tear variables: component flows, enthalpy flow, pressure. Convergence: bounded Wegstein, q ∈ [−5, 0], first two steps plain substitution (Wegstein 1958; Seider et al. 2009 §5.4); `recycle_method="direct"` available. Tolerance 1e-8 relative on flows, pressure and temperature; at most 200 iterations. Start value: the tear stream's own state if fully given, else an empty stream. Results report an info message (tear streams, iterations, method); non-convergence is an error on the first tear stream. A mixer's default pressure now ignores empty inlets (an empty stream has no physical pressure). User choice of tear streams and method in the UI: later. — accepted
