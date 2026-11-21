# QUESTIONS for the maintainer (Berkay)

Answer under each question (or in an issue). Agents: if unanswered, use the stated default.

## Open

**Q2 · Branch protection on `main`.** Please enable in GitHub → Settings → Branches: require a pull request, 1 approval, passing checks.
Default: agents never push to `main` anyway.

**Q3 · Product name.** Working name "Open Process Design" (repo `simulator`). Keep it?
Default: keep.

**Q5 · Antoine constants check (T04 test).** The Raoult hand-calculation test uses benzene/toluene Antoine constants cited as Felder & Rousseau, Table B.4 (benzene 6.89272 / 1203.531 / 219.888; toluene 6.95805 / 1346.773 / 219.693; log10 mmHg, °C). Please compare with your copy of the book and correct them in `engine/tests/test_reference_adapter.py` if they differ.
Default: keep; the test tolerance (ΔVF ≤ 0.01) also covers other common Antoine sets.

## Answered

**Q1 · Server for DWSIM.** No server for now; team is Berkay + Claude. → D011, D012 (DWSIM after the demo).

**Q4 · Demo hosting.** Free: GitHub Pages, engine in the browser. → D011.
