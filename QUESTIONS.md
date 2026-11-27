# QUESTIONS for the maintainer (Berkay)

Answer under each question (or in an issue). Agents: if unanswered, use the stated default.

## Open

**Q9 · HDA column specifications (optional).** The CHEMCAD stream table does not include the column settings. If you send stages, feed stage, reflux ratio and condenser/reboiler duties of columns 15 and 16 (and the thermo method, to confirm SRK), the HDA case can use rigorous columns and compare their duties.
Default: FUG shortcut columns with the key recoveries from the stream table (docs/VALIDATION.md).
Answer (2026-11-27, Berkay): will send a screen recording of the CHEMCAD settings.

## Answered

**Q8 · HDA CHEMCAD case.** Stream table received 2026-11-27 (CHEMCAD 8.1, 25 streams). → `examples/hda-chemcad-validation.opd.json`, `engine/tests/test_hda_chemcad.py`, D033.

**Q3 · Product name.** Answer (2026-11-27, Berkay): keep "Open Process Design".

**Q2 · Branch protection on `main`.** Answer (2026-11-27, Berkay): enable it. A classic branch protection rule for `main` (pull request, 1 approval, `test` check passing) was filled in by Claude in the browser; Berkay confirms it with his password (GitHub sudo mode). Admins may bypass, because agent PRs are opened under the maintainer's account and GitHub does not let an author approve his own PR.

**Q6 · GitHub Pages.** Done 2026-11-21 (Source: GitHub Actions); the demo is live at https://open-processdesign.github.io/simulator/.

**Q1 · Server for DWSIM.** No server for now; team is Berkay + Claude. → D011, D012 (DWSIM after the demo).

**Q4 · Demo hosting.** Free: GitHub Pages, engine in the browser. → D011.

**Q5 · Antoine constants check (T04 test).** The Raoult hand-calculation test uses benzene/toluene Antoine constants cited as Felder & Rousseau, Table B.4 (benzene 6.89272 / 1203.531 / 219.888; toluene 6.95805 / 1346.773 / 219.693; log10 mmHg, °C). Please compare with your copy of the book and correct them in `engine/tests/test_reference_adapter.py` if they differ.
Default: keep; the test tolerance (ΔVF ≤ 0.01) also covers other common Antoine sets.
Answer (2026-11-21, Berkay): checked — keep.

**Q7 · Methanol–water VLE check (T12 test).** The NRTL test compares with methanol–water data at 1 atm: (x, y, T °C) = (0.10, 0.418, 87.7), (0.30, 0.665, 78.0), (0.50, 0.779, 73.1), (0.80, 0.915, 67.6), cited as Perry's Handbook. Please confirm against your copy (or a lab-course table).
Default: keep; tolerances are 0.7 K and 0.02 in y.
Answer (2026-11-21, Berkay): checked — keep.
