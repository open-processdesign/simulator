# QUESTIONS for the maintainer (Berkay)

Answer under each question (or in an issue). Agents: if unanswered, use the stated default.

## Open

**Q2 · Branch protection on `main`.** Please enable in GitHub → Settings → Branches: require a pull request, 1 approval, passing checks.
Default: agents never push to `main` anyway.

**Q3 · Product name.** Working name "Open Process Design" (repo `simulator`). Keep it?
Default: keep.

**Q5 · Antoine constants check (T04 test).** The Raoult hand-calculation test uses benzene/toluene Antoine constants cited as Felder & Rousseau, Table B.4 (benzene 6.89272 / 1203.531 / 219.888; toluene 6.95805 / 1346.773 / 219.693; log10 mmHg, °C). Please compare with your copy of the book and correct them in `engine/tests/test_reference_adapter.py` if they differ.
Default: keep; the test tolerance (ΔVF ≤ 0.01) also covers other common Antoine sets.

**Q6 · Turn on GitHub Pages (T10).** Settings → Pages → Build and deployment → Source: **GitHub Actions**. After that, every merge to `main` publishes the demo at https://open-processdesign.github.io/simulator/.
Default: until this is done the `pages` workflow fails at the deploy step; nothing else is affected.

**Q7 · Methanol–water VLE check (T12 test).** The NRTL test compares with methanol–water data at 1 atm: (x, y, T °C) = (0.10, 0.418, 87.7), (0.30, 0.665, 78.0), (0.50, 0.779, 73.1), (0.80, 0.915, 67.6), cited as Perry's Handbook. Please confirm against your copy (or a lab-course table).
Default: keep; tolerances are 0.7 K and 0.02 in y.

## Answered

**Q1 · Server for DWSIM.** No server for now; team is Berkay + Claude. → D011, D012 (DWSIM after the demo).

**Q4 · Demo hosting.** Free: GitHub Pages, engine in the browser. → D011.
