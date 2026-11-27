# Changelog

All notable changes. Versions follow [Semantic Versioning](https://semver.org/); dates are UTC.

## [Unreleased]

### Changed
- HDA CHEMCAD example: one reactor with both reactions, as in the design drawing (CHEMCAD uses
  two in series); compressor powers checked against the CHEMCAD dialogs (within 0.2 %).

## [0.1.1] — 2026-11-27

### Added
- HDA plant validated against the maintainer's CHEMCAD 8.1 case (`hda-chemcad-validation`, SRK):
  flows within 0.2 %, temperatures within 0.2 K (compressor outlet 1.3 K), duties within 0.7 %.
- Shortcut column: optional condenser temperature (partial condenser with a drum for off-gas) and
  column pressure drop; both described in the user guide (EN/TR).

### Fixed
- Shortcut column: no NaN when a component is absent from the feed; clear message when the
  distillate cannot be condensed at the column pressure.
- Compressed light gases above their pseudo-critical temperature are reported as vapour.

## [0.1.0] — 2026-11-22

First public release: a general-purpose steady-state simulator in the browser, checked against
published cases. See `docs/VALIDATION.md` for every check and its tolerance.

### Workflow and interface
- Components → Thermodynamics → Flowsheet → Run → Results, English and Turkish.
- 1347 components from the MIT-licensed `chemicals` database; search by name, formula or CAS.
- Flowsheet canvas with palette, side-panel settings, status dots, clear issue messages that
  jump to the unit or stream.
- Unit sets SI / Metric / English; CSV export (Excel-ready, decimal comma in Turkish).
- Profiles as charts and tables: column stages, PFR axial profiles, heat-exchanger T–Q curves.
- Save and open `.opd.json` files; 15 examples.

### Thermodynamics
- Ideal (Raoult), Peng–Robinson, SRK (k_ij from the ChemSep database or the user),
  NRTL and UNIQUAC (ChemSep tables or user parameters; missing pairs reported).
- Robust flashes: P–VF, bubble/dew and P–H fallbacks for `thermo` 0.6.1 edge cases;
  pure-component streams inside mixtures.

### Unit operations
- Feed, product, mixer, splitter, flash, heater/cooler, valve, pump, compressor.
- Heat exchanger: zone analysis with phase boundaries, internal pinch, rating on zoned UA;
  optional shell-and-tube geometry by Kern's method (U, area, F-factor, pressure drops).
- Reactors: conversion, CSTR and PFR (power-law kinetics), equilibrium (gas or liquid phase,
  K from formation data or a user correlation).
- Columns: shortcut (Fenske–Underwood–Gilliland) and rigorous (MESH, bubble-point method).
- Recycle loops: tear streams found automatically, bounded Wegstein acceleration, start
  estimates on tear streams.

### Validation
- VLE against experiment (benzene–toluene, methanol–water, ethanol–water azeotrope).
- Turton's cumene Unit 800 (duties within 3 %) and DME Unit 200 (reactor within 2.6 K).
- HDA plant template; the CHEMCAD-validated HDA case follows when its stream table is available.

### Known limitations
- Kern's method is single-phase; Bell–Delaware is not implemented.
- Missing binary pairs are treated as ideal (e.g. DME–methanol, DME–water in NRTL).
- DWSIM engine is planned behind the same adapter (needs a server).
