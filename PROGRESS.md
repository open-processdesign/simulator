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

## 2026-11-21 — Claude (maintainer-requested session) — T04
- Done: `engine/opd_engine/adapters/reference.py` — sequential-modular solver on MIT `thermo` (0.6.1): feed, product, mixer, splitter, heater, valve, flash (PT, PQ, P-VF); IDEAL (Raoult), PR, SRK; k_ij from document → ChemSep table → 0 with warning; validation issues for missing/conflicting/non-SI specs, ports, recycle (until T08), unknown CAS, thermo failures. Registered as engine `reference`. 14 new issue messages in EN/TR. Engine CI now installs `thermo`.
- Tests: 46 passed. Checks: flash-drum balances; IDEAL flash vs. Raoult + Antoine (Felder & Rousseau, Table B.4) hand calculation; PR/SRK pure-component boiling points vs. NIST WebBook; heater T ⇄ duty round trip; isenthalpic valve; mixer/splitter balances; adiabatic flash; user k_ij; issue codes all translated; result document valid against the JSON Schema.
- PR: #4 (based on PR #2).
- Next: T03 (Pyodide spike: run this adapter in the browser).
