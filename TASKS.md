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
| T01 | **Web scaffold.** `web/`: Vite + React + TypeScript + Tailwind + shadcn/ui. Load `design/tokens.css`, fonts (Geist, Geist Mono, Source Serif 4, self-hosted). i18next with `web/locales/en.json` + `tr.json`, language switch. App shell: top bar + 5-step workflow nav (Components, Thermodynamics, Flowsheet, Run, Results) with empty pages. Vitest + one smoke test. GitHub Actions CI for web. | – | review (PR #3) |
| T02 | **OPD models.** `engine/opd_engine/models.py`: Pydantic v2 models matching `schema/flowsheet.schema.json`; load/validate `examples/*.opd.json`; pytest; CI job for Python. `[handoff-ok]` | – | review (PR #2) |
| T03 | **Engine runtime spike.** Run `opd_engine` + `thermo` in the browser with Pyodide inside a Web Worker; solve `examples/flash-drum.opd.json` from a test page. Record load time and size. If it fails, fall back to a FastAPI service on a free container host (see D012). | T02 | review (PR #5) |
| T04 | **Reference adapter.** `engine/opd_engine/adapters/reference.py` using MIT `thermo`: Feed, Mixer, Splitter, Heater/Cooler, Valve, Flash (PT and PQ), PR/SRK/ideal. Sequential-modular solve for acyclic flowsheets. Tests vs. textbook flash example (cite source). | T02 | review (PR #4, on PR #2) |
| T05 | **Components + Thermodynamics pages.** Component search/add/remove (`chemicals` database via the engine runtime), thermo package select, binary-parameter source table (database / user / missing → k_ij = 0). | T01, T03 | review (PR #6) |
| T06 | **Flowsheet canvas.** React Flow (`@xyflow/react`, MIT): unit palette by category, drag-drop, connect ports → streams, side panel for unit/stream specs, status dots. State = OPD document. | T01, T02 | review (PR #7) |
| T07 | **Run + Results.** Run button → engine runtime; stream table (T, P, flow, phase fraction, composition), unit results, issue list that highlights the unit/stream on the canvas. | T04, T06 | wip |
| T08 | **Recycle loops.** Tear-stream selection + Wegstein / direct substitution in the reference adapter, with convergence report. Cite textbook source. | T04 | todo |
| T09 | **More demo units** (reference adapter, from textbooks): Pump, Compressor, Heat exchanger (two-stream, energy balance), Conversion reactor, Shortcut column (Fenske–Underwood–Gilliland). One unit per session if needed. | T04 | todo |
| T10 | **Save/load + deploy.** Save/open OPD JSON file, example gallery (flash drum, simple HDA-like loop), disclaimer banner, GitHub Pages deployment via Actions. | T07 | todo |
| T11 | **Demo check.** Build one process end-to-end in both languages, fix blockers, update README with link and screenshots. | T08, T09, T10 | todo |

## After the demo — DWSIM engine (needs a host, see D012)
| ID | Task | Depends | Status |
|---|---|---|---|
| T20 | **DWSIM headless spike.** Docker image running DWSIM automation on Linux; solve the flash example from a script. Try a free container host. Record findings in DECISIONS.md. | – | todo |
| T21 | **DWSIM adapter + engine service.** OPD → DWSIM translation, run, map results back; separate service behind the adapter interface. Shadow-compare with `reference`. | T20 | todo |

## M2 / M3 — later (to be detailed after the demo)
- Rigorous column, kinetic reactors, rigorous HX, unit sets, CSV export.
- Validation suite + `docs/VALIDATION.md` (HDA vs. CHEMCAD, methanol, cumene).
- Demo video, user guide, CONTRIBUTING.md, CODE_OF_CONDUCT.md.
