# Design system

Calm, simple, easy on the eyes. **Colour only where it means something.**
Tokens live in [`design/tokens.css`](../design/tokens.css); components must use tokens, never raw hex values.

## Principles
1. **Quiet surfaces.** Warm off-white background, white panels, soft black text. No pure black, no pure white backgrounds, no harsh contrast.
2. **One accent.** Orange marks the primary action, the selection and the current workflow step. Never decoration.
3. **Meaningful colour only:** unit categories (palette icons), stream phases (canvas lines), status dots, temperature heat-map after a run.
4. **Numbers are first-class.** Tabular, monospaced, right-aligned, units always visible.
5. **CHEMCAD habits.** Unit palette on the left, canvas in the centre, settings in a **side panel** on the right (no pop-up windows), stream table below.

## Colour
| Role | Token | Value |
|---|---|---|
| Background | `--opd-bg` | #FAF8F4 |
| Panel | `--opd-surface` | #FFFFFF |
| Muted panel | `--opd-surface-muted` | #F3F0EA |
| Border | `--opd-border` | #E6E1D8 |
| Text | `--opd-text` | #1F1D1A (soft black) |
| Secondary text | `--opd-text-muted` | #6B655C |
| Accent | `--opd-accent` | #D9733B |
| Accent soft | `--opd-accent-soft` | #F8E6DA |

Status: solved `--opd-ok`, missing input `--opd-warn`, error `--opd-error`, info `--opd-info`.
Phases: vapour, liquid, mixed, solid — see tokens. Status is never colour-only: dots carry an icon/tooltip.

## Typography
All fonts are free (SIL Open Font License) and self-hosted.
- **Geist** — UI text, labels, buttons. Base 14 px, line height 1.5.
- **Geist Mono** — numbers in tables and inputs (`font-variant-numeric: tabular-nums`).
- **Source Serif 4** — page titles and empty-state headings only; gives a calm, editorial feel.

Scale: 12 / 13 / 14 / 16 / 20 / 26 px. Weights: 400, 500, 600.

## Spacing, shape, depth
4 px grid (4, 8, 12, 16, 24, 32). Radius 6 / 10 / 14 px. One soft shadow for floating elements; panels use borders, not shadows.

## Layout
```
┌──────────────────── top bar (48) : logo · project name · workflow steps · Run · language ────┐
├ palette (220) ┬──────────── canvas ───────────────┬──────── side panel (340) ─────────┤
│ by category   │ units, streams, status dots       │ selected unit / stream settings    │
│               ├───────────────────────────────────┤                                    │
│               │ stream table / issues (resizable) │                                    │
└───────────────┴───────────────────────────────────┴────────────────────────────────────┘
```
Workflow steps: **Components → Thermodynamics → Flowsheet → Run → Results**. Current step in accent; completed steps with a check.

## Components (shadcn/ui, themed with tokens)
Button (primary = accent, secondary = outline, ghost), Input with unit suffix, Select, Tabs, Table (sticky header, zebra off), Badge, Status dot, Tooltip, Toast, Side panel, Command palette (search units/components).

## Messages
Plain language, say **where** and **what**: "Flash F-101: outlet pressure is missing." not "Convergence failed". Each message links to the unit/stream it refers to.

## Language
English default, Turkish second. No hard-coded strings; keys in `web/locales/{en,tr}.json`. Numbers formatted by locale (decimal comma in Turkish).

## Accessibility
WCAG AA contrast for text, visible focus ring (`--opd-focus`), full keyboard use of the canvas palette and side panel.
