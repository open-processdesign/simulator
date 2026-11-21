# web — Open Process Design front-end

Vite + React + TypeScript + Tailwind CSS v4 + shadcn/ui (themed with `../design/tokens.css`), i18next (EN/TR).

```bash
npm ci
npm run dev      # http://localhost:5173
npm test         # Vitest
npm run build    # type-check + production build to dist/
```

- Design tokens are imported from `design/tokens.css` and exposed to Tailwind in `src/index.css` (`bg-surface`, `text-muted`, `text-accent`, …). Never use raw hex values in components.
- Fonts (Geist, Geist Mono, Source Serif 4; SIL OFL) are self-hosted via Fontsource packages and bundled into `dist/`.
- All user-visible strings live in `locales/en.json` and `locales/tr.json`; a test checks both files have the same keys.
- Workflow step routing uses the URL hash (`#/flowsheet`) so the static build works on GitHub Pages.
- New shadcn/ui components: copy from the shadcn registry into `src/components/ui/` and theme them with tokens (see `components.json`).
