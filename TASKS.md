# TASKS

Status: `todo` · `wip` · `review` · `done` · `blocked`. Tag `[handoff-ok]` = ChatGPT may take it.
Agents take the **first unblocked `todo`** from top to bottom (see `AGENTS.md`).

Night sessions until the demo (Mon/Wed/Sat): 21, 23, 25, 28, 30 Nov · 2, 5, 7, 9, 12, 14 Dec → 11 sessions, about one task each.

## M0 — Foundations
| ID | Task | Status |
|---|---|---|
| T00 | Repo, agent rules, roadmap, design system, OPD schema v0.1, adapter interface | done |

## M1 — Working demo (target 15 Dec 2026)
| ID | Task | Depends | Status |
|---|---|---|---|
| T01 | **Web scaffold.** `web/`: Vite + React + TypeScript + Tailwind + shadcn/ui. Load `design/tokens.css`, fonts (Geist, Geist Mono, Source Serif 4, self-hosted). i18next with `web/locales/en.json` + `tr.json`, language switch. App shell: top bar + 5-step workflow nav (Components, Thermodynamics, Flowsheet, Run, Results) with empty pages. Vitest + one smoke test. GitHub Actions CI for web. | – | todo |
| T02 | **OPD models.** `engine/opd_engine/models.py`: Pydantic v2 models matching `schema/flowsheet.schema.json`; load/validate `examples/*.opd.json`; pytest; CI job for Python. `[handoff-ok]` | – | todo |
| T03 | **API service.** `api/` FastAPI: `GET /health`, `POST /validate`, `POST /simulate` (calls adapter registry), `GET /components?q=` (search via `chemicals`). Error responses use the structured `Issue` model. Tests with httpx. | T02 | todo |
| T04 | **Reference adapter.** `engine/opd_engine/adapters/reference.py` using MIT `thermo`: Feed, Mixer, Splitter, Heater/Cooler, Valve, Flash (PT and PQ), PR/SRK/ideal. Sequential-modular solve for acyclic flowsheets. Tests vs. textbook flash example (cite source). | T02 | todo |
| T05 | **Components + Thermodynamics pages.** Component search/add/remove (API), thermo package select, binary-parameter source table (database / user / missing → k_ij = 0). | T01, T03 | todo |
| T06 | **Flowsheet canvas.** React Flow (`@xyflow/react`, MIT): unit palette by category, drag-drop, connect ports → streams, side panel for unit/stream specs, status dots. State = OPD document. | T01, T02 | todo |
| T07 | **Run + Results.** Run button → `/simulate`; stream table (T, P, flow, phase fraction, composition), unit results, issue list that highlights the unit/stream on the canvas. | T04, T06 | todo |
| T08 | **DWSIM headless spike** (with server owner). Docker image running DWSIM automation on Linux; solve `examples/flash-drum.opd.json` equivalent from a script. Record findings in DECISIONS.md. | – | todo |
| T09 | **DWSIM adapter + engine service.** OPD → DWSIM flowsheet translation, run, map results back; runs as a separate service behind the adapter interface. Shadow-compare with `reference` on the flash example. | T08 | todo |
| T10 | **Demo units.** Pump, Compressor, Heat exchanger, Conversion reactor, Shortcut column, recycle loops (via DWSIM adapter; reference adapter where trivial). | T09 | todo |
| T11 | **Save/load + deploy.** Save/open OPD JSON file, example gallery (flash drum, simple HDA-like loop), disclaimer banner, `docker compose` for web + api + engine, deploy notes. | T07, T09 | todo |
| T12 | **Demo check.** Build one process end-to-end in both languages, fix blockers, update README with link and screenshots. | T10, T11 | todo |

## M2 / M3 — later (to be detailed after the demo)
- Rigorous column, kinetic reactors, rigorous HX, unit sets, CSV export.
- Validation suite + `docs/VALIDATION.md` (HDA vs. CHEMCAD, methanol, cumene).
- Demo video, user guide, CONTRIBUTING.md, CODE_OF_CONDUCT.md.
