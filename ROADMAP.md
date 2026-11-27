# ROADMAP

Scope rule: chemical engineering first. Other disciplines only after Phase 1 is validated.

## Phase 1 — Chemical engineering core (Nov 2026 – Mar 2027)

### Milestone M0 — Foundations (done 13 Nov 2026)
Repo, agent rules, design system, engine-independent data format, adapter interface.

### Milestone M1 — Working demo (target: 15 Dec 2026, latest 22 Dec)
"Any process can be built and simulated from a link."
- Web app: Components → Thermodynamics → Flowsheet → Run → Results.
- Flowsheet canvas with unit palette: Feed, Product, Mixer, Splitter, Flash, Heater/Cooler, Heat exchanger, Pump, Compressor, Valve, Conversion reactor, Shortcut column.
- Side panel for unit settings; stream table; status dots (solved / missing input / error).
- Thermo: Peng–Robinson, SRK, NRTL, ideal (Raoult).
- Engine: in-house `reference` adapter (MIT `thermo`) running in the browser (Pyodide). No server needed (D011). DWSIM follows after the demo (D012).
- Recycle loops: own tear-stream solver (Wegstein / direct substitution).
- Clear error messages for missing inputs.
- English + Turkish UI. Save/load OPD JSON files (no accounts yet).
- Deployed on GitHub Pages (free) with the "education and preliminary design" notice.

### Milestone M2 — Rigorous units + DWSIM (Jan 2027)
DWSIM engine service on a free/cheap host (T90–T91), shadow-compared with `reference`. Rigorous distillation column, equilibrium/PFR/CSTR reactors, shell-and-tube exchanger, component database search, unit sets (SI / metric / English), result export (CSV).

### Milestone M3 — Validated release v0.1 (target: 15 Mar 2027)
- Validation suite: HDA (vs. maintainer's CHEMCAD case — done, T29), plus 2–3 literature cases (cumene, DME — done).
- Acceptance criterion for each key result: |x_new − x_ref| / |x_ref| < ε (ε recorded per quantity in `docs/VALIDATION.md`).
- Validated HDA template shipped in the app.
- 2-minute demo video, user guide, contributor guide.

## Phase 2 — after March 2027
User accounts, MCP server (users' own Claude operates the site), process template library, parameter library with provenance, VLE regression wizard, first own engine modules in shadow mode.

## Phase 3+ — later
Equipment design workspace (pumps, piping, NPSH, vessels), then bioprocess and energy cycles. Each workspace owned and validated by volunteers of that discipline.
