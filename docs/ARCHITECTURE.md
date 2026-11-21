# Architecture

> **Demo phase (since 2026-11-20, DECISIONS.md D011/D014):** there is no API service yet. The web app runs
> `engine/opd_engine` (OPD models, adapter interface, reference engine) inside a Web Worker on Pyodide and calls
> `opd_engine.runtime` directly. The layers below remain the target once DWSIM joins as a separate service (D012);
> the runtime's JSON shape is the same one the API will return.

## Layers
```
┌───────────────┐  OPD JSON   ┌──────────────┐  OPD JSON   ┌───────────────────┐
│  Web UI       │ ──────────► │  API service │ ──────────► │  Engine adapter    │
│  React/TS     │ ◄────────── │  FastAPI     │ ◄────────── │  (interface)       │
└───────────────┘  results    └──────────────┘  results    └─────────┬─────────┘
                                                                     │
                                         ┌───────────────────────────┼───────────────────┐
                                         ▼                           ▼                   ▼
                                  DWSIM adapter              reference adapter      own modules
                                  (separate service,         (MIT `thermo`,         (later, shadow
                                   pinned DWSIM version)      tests + fallback)      mode first)
```

- **Web UI** only knows the OPD format and the API. No engine concepts.
- **API service** validates documents, picks an adapter, returns results and structured issues.
- **Engine adapter** is the only code that talks to an engine. Interface: [`engine/opd_engine/adapter.py`](../engine/opd_engine/adapter.py).
- **DWSIM** runs as its own process/container (GPL boundary, crash isolation, can be restarted or scaled). Its files are never the source of truth.

## OPD flowsheet format (v0.1)
Schema: [`schema/flowsheet.schema.json`](../schema/flowsheet.schema.json). Example: [`examples/flash-drum.opd.json`](../examples/flash-drum.opd.json).

A document has:
- `components` — identified by CAS number + name.
- `thermo` — property package (`PR`, `SRK`, `NRTL`, `IDEAL`, …) and optional binary parameters, each with `source` (database / user / literature + reference).
- `units` — id, type, ports, specs. Unit types are engine-neutral (`flash`, `heater`, `mixer`, …).
- `streams` — id, from/to port, and (for feeds) state specs.
- `results` — optional, written by the engine run; includes `engine` name + version so results are traceable.
- `layout` — canvas positions, kept separate from process data.

All values in SI. Each spec is `{ "value": number, "unit": "K" }`; the unit is stored for clarity but must be SI in v0.1.

## Simulation request flow
1. UI sends the OPD document to `POST /simulate` (optional `engine`, default from config).
2. API validates against the schema → returns `issues` if inputs are missing (no engine call).
3. Adapter translates OPD → engine model, runs, maps results back to OPD `results`.
4. In **shadow mode**, a second adapter runs the same document; differences above ε are logged, not shown.

## Issues (errors and warnings)
`{ severity: "error"|"warning"|"info", code, message_key, params, target: { kind: "unit"|"stream"|"thermo"|"component", id } }`
`message_key` maps to `web/locales/*.json` so issues are translated; `target` lets the UI highlight the item.

## Engine replacement (strangler fig)
1. DWSIM computes everything.
2. A new module runs in shadow mode next to DWSIM; the system compares results.
3. After tests and real-use agreement within ε, a human switches it on; DWSIM stays as fallback.
4. Order: thermodynamics → simple units → reactors → columns.

Own modules are written from textbooks/papers or MIT-licensed libraries (no DWSIM code), so they can belong fully to the project.

## Disciplines
Workspaces per discipline (chemical engineering first) share one engine layer and one database; a workspace only filters which units and templates a user sees. Defined in Phase 3.

## Repository layout (target)
```
web/        React app (T01)
api/        FastAPI service (T03)
engine/     opd_engine package: models, adapter interface, adapters
schema/     JSON Schemas
examples/   Example flowsheets (also used as tests)
design/     Design tokens
docs/       Architecture, design system, validation
```
