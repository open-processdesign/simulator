# Contributing to Open Process Design

Thank you for helping. You do not need to write code to contribute.

## Ways to help

- **Validate results.** Build a process you know (from a course, a textbook or a commercial simulator) and compare. Report differences with your reference values and their source.
- **Add examples.** A clear `.opd.json` file in `examples/` with a short description becomes part of the gallery and of the test suite.
- **Literature parameters.** Binary interaction parameters (k_ij, NRTL b_ij/α) with a citation.
- **Translations.** `web/locales/en.json` and `web/locales/tr.json`; a test checks both have the same keys.
- **Bug reports.** Attach the `.opd.json` file (File → Save as file) and say what you expected.

## Ground rules for code

- Read `AGENTS.md` (rules for humans and AI agents alike), `DECISIONS.md` and the task in `TASKS.md` first.
- One task per pull request; never push to `main`; tests must pass (`engine`: `pytest`, `web`: `npm test`).
- **Numbers come from the engine, never typed in by hand.** Every model has a test against an independent reference (closed-form solution, textbook data, experimental data) and cites the source in its docstring.
- Internal units are SI; conversions only in `web/src/units/`.
- No DWSIM source code in this repository. Own modules are written from textbooks, papers or MIT-licensed libraries (`thermo`, `chemicals`).
- Code, comments, docs and commits in English; user-visible text through the locale files.

## Development setup

```bash
cd engine && pip install -e ".[dev,reference]" && pytest
cd web && npm ci && npm run dev
```

The web app runs the Python engine in the browser (Pyodide). See `web/README.md` for running it against a local Pyodide build.

## Licence

By contributing you agree that your code is released under GPL-3.0 and your data contributions under CC BY 4.0 (see `DECISIONS.md` D001).
