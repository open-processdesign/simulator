# AGENTS.md — rules for every AI agent

Applies to Claude, ChatGPT and any other agent working on this repo. Humans decide; agents propose.

## 1. Start of every session
1. Read, in order: `AGENTS.md`, `ROADMAP.md`, `TASKS.md`, the last 3 entries of `PROGRESS.md`, `DECISIONS.md`, `QUESTIONS.md`.
2. Check for answered questions in `QUESTIONS.md` and apply them.
3. Apply the **lock rule** (below) before touching anything.

## 2. Lock rule (mandatory)
- Before starting work, open a **draft pull request** whose title starts with `[WIP]`.
- If any open PR titled `[WIP] …` was created or updated **less than 6 hours ago** by another agent/session, **do not start**. Log one line in your final message and stop.
- A `[WIP]` PR older than 6 hours is stale: you may continue it or close it with a comment explaining why.
- When done, remove `[WIP]` from the title and mark the PR "Ready for review".

## 3. One task per session
- Take the **first `todo` task** in `TASKS.md` that is not blocked (respect the current phase order).
- If a task is too big for one session, split it in `TASKS.md`, do the first part only.
- `ChatGPT` may only take tasks tagged `[handoff-ok]`, on its own branch.

## 4. Branches and PRs
- Never push to `main`. Branch name: `agent/<task-id>-<short-name>` (e.g. `agent/T05-flash-api`).
- One PR per task. PR description: what changed, how it was tested, open risks.
- `main` is protected: nothing merges without passing tests and human approval.

## 5. Quality bar
- Every code change ships with tests; run them before opening the PR.
- **Numbers come from the engine, never from a language model.** No hard-coded "plausible" results.
- Internal units: SI (K, Pa, mol/s, J/mol). Convert only at the UI edge.
- Never put engine-specific objects in the OPD format, the API or the UI. Only the adapter talks to an engine.
- Do not copy DWSIM source code into this repo. Own modules are written from textbooks/papers or MIT-licensed libraries (e.g. `thermo`, `chemicals`); cite the source in a docstring.
- Follow `docs/DESIGN_SYSTEM.md` for any UI work. All user-visible strings go through `web/locales/` (English + Turkish).
- Code, comments, docs and commit messages in **English**.

## 6. End of every session
1. Update `TASKS.md` (status), append an entry to `PROGRESS.md` (template inside).
2. Record any non-trivial choice in `DECISIONS.md`.
3. If blocked on a human decision, add it to `QUESTIONS.md` and pick a sensible default when possible (say which).
4. Keep the session small: stop after one task. Do not start a second one.

## 7. Never
- Share or request passwords, tokens or account access.
- Disable tests, branch protection or CI to make something pass.
- Delete files you did not create in this task without a note in the PR.
- Spin up parallel agents.
