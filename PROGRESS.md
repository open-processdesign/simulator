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

## 2026-11-21 — Claude (maintainer-requested session) — T01
- Done: `web/` scaffold — Vite 8 + React 19 + TS + Tailwind v4 (tokens from `design/tokens.css` via `@theme`) + shadcn/ui setup (`components.json`, `cn`, themed Button). Self-hosted fonts (Fontsource: Geist, Geist Mono, Source Serif 4). i18next with EN/TR + language switch (remembered in localStorage). App shell: top bar, 5-step workflow nav (hash routing), empty step pages, disclaimer footer. Web CI (`.github/workflows/web.yml`).
- Tests: Vitest 5 passed (steps, navigation, Turkish switch, hash parsing, EN/TR key parity); `npm run build` OK.
- PR: #3.
- Note: the 21 Nov night run did nothing — the scheduled task had no GitHub repo attached. Fixed for this session; the scheduled task must be recreated with the repo attached.
- Next: T03 (in-browser engine spike), building on T02 (PR #2).
