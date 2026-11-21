# PROGRESS

Append one entry per session, newest at the bottom. Keep it short.

Template:
```
## YYYY-MM-DD — <agent> — <task id>
- Done:
- Tests:
- PR:
- Next / blockers:
```

---

## 2026-11-13 — Claude (setup session) — T00
- Done: repo skeleton; AGENTS.md with lock rule; ROADMAP (Phase 1, M0–M3); TASKS (T01–T12 for the December demo); DECISIONS D001–D010; design system + tokens; OPD flowsheet schema v0.1 + flash-drum example; engine adapter interface (Python); EN/TR locale seeds; GPL-3.0 license.
- Tests: `engine/tests` — example validates against schema; adapter registry smoke test.
- PR: initial commit on `main` (repo was empty).
- Next: nightly developer agent starts 21 Nov with T01. 16–20 Nov: no automated work (exam week).
- Blockers: headless DWSIM on Linux unverified (T08, needs server). Open questions in QUESTIONS.md.

## 2026-11-20 — Claude (maintainer session) — T02 + plan change
- Done: PR #1 (no-server plan, D011/D012) merged; `main` protected by a ruleset (PR required, no force push/deletion). T02: `opd_engine/models.py` (Pydantic v2 models mirroring the schema, `load()`, `to_dict()`, `check_references()` returning user-facing `Issue`s); new issue keys in EN/TR locales.
- Tests: 23 passed (round-trip example ⇄ model ⇄ JSON Schema; structural errors rejected by both; cross-reference issues).
- PR: #2.
- Next: T01 tonight (web scaffold), then T03 (in-browser engine spike).

## 2026-11-21 — Claude (maintainer-requested session) — T01
- Done: `web/` scaffold — Vite 8 + React 19 + TS + Tailwind v4 (tokens from `design/tokens.css` via `@theme`) + shadcn/ui setup (`components.json`, `cn`, themed Button). Self-hosted fonts (Fontsource: Geist, Geist Mono, Source Serif 4). i18next with EN/TR + language switch (remembered in localStorage). App shell: top bar, 5-step workflow nav (hash routing), empty step pages, disclaimer footer. Web CI (`.github/workflows/web.yml`).
- Tests: Vitest 5 passed (steps, navigation, Turkish switch, hash parsing, EN/TR key parity); `npm run build` OK.
- PR: #3.
- Note: the 21 Nov night run did nothing — the scheduled task had no GitHub repo attached. Fixed for this session; the scheduled task must be recreated with the repo attached.
- Next: T03 (in-browser engine spike), building on T02 (PR #2).

## 2026-11-21 — Claude (maintainer-requested session) — T04
- Done: `engine/opd_engine/adapters/reference.py` — sequential-modular solver on MIT `thermo` (0.6.1): feed, product, mixer, splitter, heater, valve, flash (PT, PQ, P-VF); IDEAL (Raoult), PR, SRK; k_ij from document → ChemSep table → 0 with warning; validation issues for missing/conflicting/non-SI specs, ports, recycle (until T08), unknown CAS, thermo failures. Registered as engine `reference`. 14 new issue messages in EN/TR. Engine CI now installs `thermo`.
- Tests: 46 passed. Checks: flash-drum balances; IDEAL flash vs. Raoult + Antoine (Felder & Rousseau, Table B.4) hand calculation; PR/SRK pure-component boiling points vs. NIST WebBook; heater T ⇄ duty round trip; isenthalpic valve; mixer/splitter balances; adiabatic flash; user k_ij; issue codes all translated; result document valid against the JSON Schema.
- PR: #4 (based on PR #2).
- Next: T03 (Pyodide spike: run this adapter in the browser).

## 2026-11-21 — Claude (maintainer-requested session) — T03
- Done: `opd_engine/runtime.py` (JSON in/out entry point shared by browser and future service). `web/src/engine/`: Pyodide bootstrap, Web Worker, promise client; `engine-test.html` developer page (progress, load timings, stream table, EN/TR). Build-time overrides for self-hosting (`VITE_PYODIDE_URL`, `VITE_WHEELS`). Node measurement test (`npm run spike:engine`, opt-in). Branch also merges T01 (the page needs the web app).
- Tests: engine 48 passed; web 5 passed + spike passed under Node; end-to-end in headless Chrome: ready in 12.6 s, example solved in 27 ms, same numbers as native.
- Result: D014 — browser engine is viable (≈ 13 s boot + ≈ 67 MB first download).
- PR: #5 (based on PR #4).
- Next: T05 (Components + Thermodynamics pages) or T06 (canvas).

## 2026-11-21 — Claude (maintainer-requested session) — T05
- Done: Components page (search by name/synonym/CAS/formula over a 1347-component index built from `chemicals`; add/remove; molar mass and Tb shown). Thermodynamics page (IDEAL / PR / SRK; NRTL shown as "coming later"; k_ij table with source badges database / user / missing → 0, editable with decimal comma, reset to database). OPD document reducer + provider; engine starts at app open with a status chip in the top bar; `runtime.binary_parameters` in the engine and worker protocol. EN/TR strings.
- Tests: engine 50 passed; web 20 passed; end-to-end in Chrome with the real engine (methane–CO2 k_ij 0.0978 from ChemSep shown as Database, benzene–toluene as Missing).
- PR: #6 (based on PR #5).
- Next: T06 (flowsheet canvas).

## 2026-11-21 — Claude (maintainer-requested session) — T06
- Done: Flowsheet step — palette by category (drag or click; unsupported units disabled), React Flow canvas with unit nodes (category icon, id, label, status dot, port handles), streams by connecting outlet → inlet, delete with Delete/Backspace, positions saved in `layout`. Side panel: label, exclusive spec groups (flash, heater, valve, mixer), splitter fractions, feed conditions (T or VF, P, flow, composition with normalize), stream info, translated engine issues. Engine `validate` entry point + worker message; `useIssues` hook. EN/TR strings.
- Tests: engine 51 passed; web 30 passed (editing reducer, palette, side panel, issues). End-to-end in Chrome with the real engine: feed → flash → two products drawn by mouse, specs entered, all status dots green.
- PR: #7 (based on PR #6).
- Next: T07 (Run + Results).

## 2026-11-21 — Claude (maintainer-requested session) — T07
- Done: Run button (top bar + Run + Results steps), Run step (counts, property method, what is missing with links), Results step (status, stale warning, messages, stream table, unit results), stream table under the canvas after a run, phase-coloured streams, solved status dots, shared selection so results/messages jump to the unit or stream on the canvas. EN/TR strings.
- Tests: web 33 passed (run → table/units/messages, stale after edit, failed run with links, run page). End-to-end in Chrome with the real engine: flash drum drawn by mouse and run in 32–40 ms; numbers equal native CPython (S2 x_benzene 0.6211, S3 0.4057, F-1 duty 1 653 369 W).
- PR: #8 (based on PR #7).
- Next: T08 (recycle loops) or T10 (save/load + deploy).

## 2026-11-21 — Claude (maintainer-requested session) — T08
- Done: `engine/opd_engine/adapters/recycle.py` (solve plan with strongly connected components and DFS tear streams; bounded Wegstein / substitution accelerator) wired into the reference adapter; convergence and non-convergence messages (EN/TR). `supports_recycle` is now true.
- Tests: engine 60 passed — plan for simple, nested and self loops; mixer–splitter loop vs. analytic R = rF/(1 − r) (r = 0.5, 0.9); Wegstein ≥ 3× fewer iterations than substitution (20 vs. 160); flash loop with liquid recycle closes component balances and matches the once-through duties; starting estimate used; non-convergence reported on the tear stream. Web 33 passed; engine still loads in Pyodide.
- PR: #9 (based on PR #8).
- Next: T09 (more units) and T10 (save/load + deploy).

## 2026-11-21 — Claude (maintainer-requested session) — T09
- Done: pump, compressor, heat exchanger, conversion reactor and shortcut column (FUG) in the reference engine with validation and EN/TR messages; all units enabled in the palette; side-panel editors for reactions (stoichiometry, key, conversion) and column keys; results show the engine's units. Examples `benzene-toluene-column.opd.json` and `hda-recycle-loop.opd.json`.
- Tests: engine 75 passed — pump power vs. ṁΔP/(ρη) for water; compressor vs. ideal-gas isentropic relation (N2, 1→3 bar); exchanger duty from both sides, LMTD/UA, temperature cross; HDA heat of reaction vs. formation enthalpies (−42 kJ/mol); shortcut column vs. closed-form binary Fenske and Underwood; all examples solve. Web 35 passed; all examples also solve in Pyodide.
- PR: #10 (based on PR #9).
- Next: T10 (save/load, example gallery, deploy).

## 2026-11-21 — Claude (maintainer-requested session) — T10
- Done: File menu (New, Open…, Save as file, Examples), editable process name, browser draft restored on reload, example gallery from `examples/` (flash drum, benzene–toluene column, HDA recycle loop), GitHub Pages workflow (test + build + deploy on push to main). EN/TR strings.
- Tests: web 41 passed (parsing, file names incl. Turkish letters, draft, gallery, open/save via the menu, bad file message). End-to-end in Chrome: HDA example opened from the menu, run in < 1 s (recycle converged in 10 iterations), Turkish UI with decimal commas, draft kept after reload.
- PR: #11 (based on PR #10). Maintainer action: Q6 (turn on Pages).
- Next: T11 (demo check, README with link and screenshots) after the PRs are merged and Pages is on.

## 2026-11-21 — Claude (maintainer-requested session) — merge + T11
- Merged PRs #2–#11 into `main` (maintainer's request), in order with merge commits; T01–T10 marked done. Turned on GitHub Pages (Source: GitHub Actions) through the maintainer's browser session; the `pages` workflow published the demo at https://open-processdesign.github.io/simulator/. Nightly scheduled task switched off (maintainer's request).
- T11 demo check: on the live site (real jsDelivr + PyPI downloads) the engine loaded and all three examples solved (flash drum 10 ms, column 40 ms, HDA loop < 1 s). End-to-end in Turkish in headless Chrome: flash drum drawn with the mouse, values typed with decimal commas, solved; same numbers as English. No blockers found.
- README: live link, how to try it, units list, screenshots, updated architecture, developer commands. ARCHITECTURE.md: note on the browser engine.
- PR: #12.
- Next (M2): rigorous units, unit sets, validation suite; see ROADMAP.md.

## 2026-11-21 — Claude (maintainer-requested session) — T12
- Done: NRTL property method in the reference engine (ChemSep NRTL parameters, user overrides, ideal fallback with warning), robust P–VF flash fallback, NRTL binary table in the UI (b_ij, b_ji, α), example `methanol-water-column-nrtl.opd.json`. EN/TR strings.
- Tests: engine 86 passed (methanol–water vs. experiment at 4 points; NRTL beats Raoult; ethanol–water azeotrope; parameter sources; τ = 0 equals Raoult). Web 42 passed. All examples solve in Pyodide.
- PR: #13 (based on PR #12).

## 2026-11-21 — Claude (maintainer-requested session) — T13
- Done: unit-set selector in the top bar (SI / Metric / English); all inputs, the stream table, unit results and component boiling points convert; storage stays SI. Top bar compacted (visually hidden labels) so it fits at 1366 px.
- Tests: web 48 passed (round trips and textbook factors, kind mapping, metric input stored as SI, psi display, metric stream table). E2E in Chrome: NRTL methanol–water example in metric units.
- PR: #14 (based on PR #13).

## 2026-11-21 — Claude (maintainer-requested session) — T14
- Done: "Export CSV" on the Results step: stream table + unit results in the current unit set, UTF-8 BOM, `,`/`.` in English and `;`/`,` in Turkish (Excel defaults), file `<process>-results.csv`; hidden when results are stale.
- Tests: web 50 passed (metric values, Turkish separators, quoting).
- PR: #15 (based on PR #14).

## 2026-11-21 — Claude (maintainer-requested session) — T15
- Done: `engine/opd_engine/adapters/column.py` (bubble-point method + θ-method), `distillation_column` unit in engine, schema, models and UI (palette, spec groups, unit-set kinds, EN/TR), example `benzene-toluene-rigorous-column.opd.json`.
- Tests: engine 94 passed — MESH residuals on every stage (component balances, y = Kx with K recomputed, summations, enthalpy balances) and overall balances; rigorous column reproduces the FUG design within a few percent (recovery, x_D, condenser duty); more reflux → purer distillate; NRTL methanol–water column; input errors. Web 50 passed; all examples solve in Pyodide (rigorous column 0.6 s).
- PR: #16 (based on PR #15).

## 2026-11-21 — Claude (maintainer-requested session) — T16
- Done: `results.profiles` in schema and models; rigorous column stores stage profiles; Results step shows temperature and liquid-composition charts (hover tooltip, legend, direct labels, unit sets) with a table view. Series colours validated with the dataviz palette validator (all hard checks pass; contrast WARN handled by labels + table).
- Tests: engine 95 passed (profiles stored, schema-valid); web 51 passed (charts, table in metric units). Rendered and checked in Chrome.
- PR: #17 (based on PR #16).

## 2026-11-21 — Claude (maintainer-requested session) — T17
- Done: `engine/opd_engine/adapters/kinetics.py` (power-law rates, CSTR and PFR solvers), `cstr`/`pfr` units in engine, schema, models and UI (palette, rate-law editor with phase, k₀, Eₐ, orders; volume/time/energy unit kinds), PFR length profiles reuse the profile charts (now generic axis), example `ethane-cracking-pfr.opd.json`. Fixes: chart x-scale for small ranges, non-overlapping end labels, exponent display for very large/small inputs.
- Tests: engine 105 passed — first-order CSTR and PFR vs. closed form at three volumes, second-order CSTR vs. its quadratic, Arrhenius dependence, adiabatic PFR outlet T equals the adiabatic conversion reactor at the same conversion, monotonic exothermic profile, input errors. Web 51 passed. Rendered in Chrome in metric units.
- PR: #18 (based on PR #17).
