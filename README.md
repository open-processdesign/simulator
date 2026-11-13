# Open Process Design — Simulator

An open-source, web-based, general-purpose chemical process simulator.
Open a link, build any flowsheet, run it, read the results — no installation, no license fee.

> **Status:** pre-alpha. Phase 1 target: a working demo in mid-December 2026, a validated release by March 2027.
> Results are for **education and preliminary design only**.

## Why

- Commercial simulators (Aspen, CHEMCAD) are expensive; many universities cannot license them.
- Free tools are powerful but hard to learn.
- Students graduate without enough hands-on simulation practice.

## What it is

- **Web-based:** runs in the browser, shareable by link.
- **General-purpose:** any process, not a fixed set of examples (HDA is only a validation case).
- **Simple workflow:** Components → Thermodynamics → Flowsheet → Run → Results.
- **Familiar to CHEMCAD users:** unit palette, side-panel settings, stream tables.
- **Clear errors:** tells you *what* is missing *where*, instead of "convergence failed".
- **Bilingual:** English (default), Turkish.

## Architecture (short)

```
Browser UI  ──►  API service  ──►  Engine adapter  ──►  Engine (DWSIM today, own modules later)
                     │
                     └── OPD flowsheet format (engine-independent JSON)
```

The UI and data never depend on a specific engine. Engines are replaced module by module
("strangler fig"): a new module runs in shadow mode next to DWSIM and is switched on only after
it matches reference results within tolerance. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

DWSIM is used as a separate service and credited as such; this project does not use the DWSIM name or logo for its own product.

## Repository map

| Path | Purpose |
|---|---|
| `ROADMAP.md` | Phases and milestones |
| `TASKS.md` | Task list (agents pick from here) |
| `PROGRESS.md` | Log of every work session |
| `DECISIONS.md` | Decisions and their reasons |
| `QUESTIONS.md` | Open questions for the maintainer |
| `AGENTS.md` | Rules for all AI agents (incl. the lock rule) |
| `docs/` | Architecture and design system |
| `schema/` | OPD flowsheet JSON Schema |
| `examples/` | Example flowsheets |
| `design/` | Design tokens |
| `engine/` | Engine adapter layer (Python) |
| `web/` | Front-end (React) — locales for now |

## Contributing

You do not need to code to help: validate results, build process templates, collect literature
parameters, translate, report bugs. Code contributions go through pull requests; `main` is protected
and nothing merges without review and passing tests.

## License

Code: [GNU GPL v3](LICENSE). Data contributions: open data license (CC BY 4.0, planned).
