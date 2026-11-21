# TASKS

Status: `todo` · `wip` · `review` · `done` · `blocked`. Tag `[handoff-ok]` = ChatGPT may take it.
Agents take the **first unblocked `todo`** from top to bottom (see `AGENTS.md`).

Night sessions until the demo (Mon/Wed/Sat): 21, 23, 25, 28, 30 Nov · 2, 5, 7, 9, 12, 14 Dec → 11 sessions, about one task each. No server: the demo runs fully in the browser (D011).

## M0 — Foundations
| ID | Task | Status |
|---|---|---|
| T00 | Repo, agent rules, roadmap, design system, OPD schema v0.1, adapter interface | done |

## M1 — Working demo (target 15 Dec 2026)
| ID | Task | Depends | Status |
|---|---|---|---|
| T01 | **Web scaffold.** `web/`: Vite + React + TypeScript + Tailwind + shadcn/ui. Load `design/tokens.css`, fonts (Geist, Geist Mono, Source Serif 4, self-hosted). i18next with `web/locales/en.json` + `tr.json`, language switch. App shell: top bar + 5-step workflow nav (Components, Thermodynamics, Flowsheet, Run, Results) with empty pages. Vitest + one smoke test. GitHub Actions CI for web. | – | done |
| T02 | **OPD models.** `engine/opd_engine/models.py`: Pydantic v2 models matching `schema/flowsheet.schema.json`; load/validate `examples/*.opd.json`; pytest; CI job for Python. `[handoff-ok]` | – | done |
| T03 | **Engine runtime spike.** Run `opd_engine` + `thermo` in the browser with Pyodide inside a Web Worker; solve `examples/flash-drum.opd.json` from a test page. Record load time and size. If it fails, fall back to a FastAPI service on a free container host (see D012). | T02 | done |
| T04 | **Reference adapter.** `engine/opd_engine/adapters/reference.py` using MIT `thermo`: Feed, Mixer, Splitter, Heater/Cooler, Valve, Flash (PT and PQ), PR/SRK/ideal. Sequential-modular solve for acyclic flowsheets. Tests vs. textbook flash example (cite source). | T02 | done |
| T05 | **Components + Thermodynamics pages.** Component search/add/remove (`chemicals` database via the engine runtime), thermo package select, binary-parameter source table (database / user / missing → k_ij = 0). | T01, T03 | done |
| T06 | **Flowsheet canvas.** React Flow (`@xyflow/react`, MIT): unit palette by category, drag-drop, connect ports → streams, side panel for unit/stream specs, status dots. State = OPD document. | T01, T02 | done |
| T07 | **Run + Results.** Run button → engine runtime; stream table (T, P, flow, phase fraction, composition), unit results, issue list that highlights the unit/stream on the canvas. | T04, T06 | done |
| T08 | **Recycle loops.** Tear-stream selection + Wegstein / direct substitution in the reference adapter, with convergence report. Cite textbook source. | T04 | done |
| T09 | **More demo units** (reference adapter, from textbooks): Pump, Compressor, Heat exchanger (two-stream, energy balance), Conversion reactor, Shortcut column (Fenske–Underwood–Gilliland). One unit per session if needed. | T04 | done |
| T10 | **Save/load + deploy.** Save/open OPD JSON file, example gallery (flash drum, simple HDA-like loop), disclaimer banner, GitHub Pages deployment via Actions. | T07 | done |
| T11 | **Demo check.** Build one process end-to-end in both languages, fix blockers, update README with link and screenshots. | T08, T09, T10 | done |
| T12 | **NRTL property package (M1 gap).** NRTL activity coefficients in the reference engine (ChemSep NRTL table → user values → missing = ideal with warning); NRTL binary-parameter table in the UI (b_ij, b_ji, α); validation vs. experimental VLE. | T05 | done |
| T13 | **Unit sets.** SI / Metric (°C, bar, kmol/h, kW) / English (°F, psia, lbmol/h, Btu/h) for every input and result in the UI; storage stays SI (D007); choice remembered per browser. | T07 | done |
| T14 | **CSV export.** Stream table and unit results as a CSV file in the current unit set; Excel-friendly in both languages (UTF-8 BOM; Turkish uses `;` and decimal comma). | T13 | done |
| T15 | **Rigorous distillation column (M2).** Equilibrium-stage column (MESH) by the bubble-point method with θ-correction: total condenser, partial reboiler, specs N, feed stage, R, D; any property package; checks vs. MESH residuals and FUG. | T09, T12 | done |
| T16 | **Column stage profiles.** Optional `results.profiles` (axis + series) in the OPD format; the rigorous column stores T, L, V, x, y per stage; Results step shows temperature and composition charts with hover and a table view. | T15 | done |
| T17 | **Kinetic reactors (M2).** CSTR and PFR with power-law kinetics (k₀, Eₐ, orders; gas or liquid concentration basis); isothermal or given duty (adiabatic); PFR length profile; checks vs. analytic first-order conversions and energy balance. | T09, T16 | done |
| T18 | **Equilibrium reactor (M2).** Gas-phase chemical equilibrium with K(T) from formation data (+ fugacity coefficients); one or more reactions; isothermal or adiabatic; checks vs. WGS correlation and equilibrium conditions. | T17 | done |
| T19 | **Docs (M3 start).** CONTRIBUTING, code of conduct, user guide (EN/TR), docs/VALIDATION.md listing every model check with reference and tolerance; README updated. | – | done |
| T20 | **Heat-exchanger rating.** Given UA (or U and area), the exchanger finds its duty from Q = UA·LMTD (counter-current) instead of a fixed outlet; UA option in the side panel. | T09 | done |
| T21 | **UNIQUAC property package.** UNIQUAC liquid (user values → ChemSep UNIQUAC table → missing = ideal with warning), r/q from UNIFAC groups; UI binary table (b_ij, b_ji). | T12 | done |
| T22 | **Zoned heat exchanger.** Equal-duty zones + bubble/dew boundaries; zoned UA, internal pinch and cross; rating on zoned UA; T–Q curves on the Results page. | T20 | done |
| T23 | **Liquid-phase equilibrium reactor.** Activities against the pure liquid; user ln K correlations; phase-mismatch warning; MTBE example. | T18 | review |
| T24 | **Shell-and-tube geometry (Kern).** Optional geometry → area, film coefficients, U, pressure drops. | T22 | review (PR #26) |
| T25 | **Literature validation case 1:** cumene Unit 800 (Turton, CHEMCAD table). | – | review |
| T26 | **Literature validation case 2:** DME Unit 200 (Turton, CHEMCAD table). | – | review |
| T27 | **HDA template from the literature base case** (swap to CHEMCAD numbers when available, Q8). | – | review |
| T28 | **v0.1 release:** demo video, CHANGELOG, final docs check. | T23–T27 | review — tag `v0.1.0` after merge |

## After the demo — DWSIM engine (needs a host, see D012; IDs T90+ so they never clash with new tasks)
| ID | Task | Depends | Status |
|---|---|---|---|
| T90 | **DWSIM headless spike.** Docker image running DWSIM automation on Linux; solve the flash example from a script. Try a free container host. Record findings in DECISIONS.md. | – | todo |
| T91 | **DWSIM adapter + engine service.** OPD → DWSIM translation, run, map results back; separate service behind the adapter interface. Shadow-compare with `reference`. | T90 | todo |

## M2 / M3 — later (to be detailed after the demo)
- Done in M2: rigorous column (T14), kinetic reactors (T17), equilibrium reactor (T18), HX rating (T20), unit sets, CSV export, docs (T19), UNIQUAC (T21), zoned HX (T22).
- Validation: HDA vs. CHEMCAD (needs Berkay's CHEMCAD stream table), methanol synthesis, cumene.
- Demo video.
