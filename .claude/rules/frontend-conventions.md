---
paths:
  - "frontend/**/*.tsx"
  - "frontend/**/*.ts"
  - "frontend/**/*.css"
---

# Frontend Conventions & Design System

## Design System Reference

The full design spec is at `docs/DESIGN.md` — READ IT FIRST before building any component.
It is the ElevenLabs-inspired editorial design system. Summary of critical rules below.

## Color Tokens (use these, never raw hex)

Define as Tailwind CSS variables or a constants file:

```
canvas:            #f5f5f5   (off-white page background)
canvas-soft:       #fafafa   (lighter section background)
ink:               #0c0a09   (primary text + CTA background)
body:              #4e4e4e   (default running text)
muted:             #777169   (subtitles, labels)
surface-card:      #ffffff   (card backgrounds)
surface-strong:    #f0efed   (badges, icon plates)
hairline:          #e7e5e4   (1px dividers, card borders)
gradient-mint:     #a7e5d3   (atmospheric orb only)
gradient-peach:    #f4c5a8   (atmospheric orb only)
gradient-lavender: #c8b8e0   (atmospheric orb only)
gradient-sky:      #a8c8e8   (atmospheric orb only)
gradient-rose:     #e8b8c4   (atmospheric orb only)
```

## Typography Rules

- **Display headings:** EB Garamond (open-source Waldenburg substitute), weight 300
  - Import: `@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@300')`
  - Sizes: 64px (hero), 48px (section), 36px (sub-section), 32px (card group)
  - Letter-spacing: negative on display (-0.32px to -1.92px)
  - **NEVER bold display text.** Weight 300 is the editorial signature.
- **Body / UI:** Inter, weight 400 (body) or 500 (labels, buttons, nav)
  - Sizes: 20px (component titles), 16px (body), 15px (small body/buttons), 14px (captions)
  - Letter-spacing: +0.15–0.18px on body text
- **Uppercase labels:** Inter 600, 12px, letter-spacing +0.96px, `text-transform: uppercase`

## Component Rules

**CTAs / Buttons:**
- Primary: background `#0c0a09` (ink), text white, `border-radius: 9999px` (pill), 40px height
- Outline: transparent background, `1px #d6d3d1` border, pill shape
- NEVER use gradient orb colors as button fills
- NEVER use a saturated accent color (no blue, no purple, no green CTAs)

**Cards:**
- Background: `#ffffff` (white) on `#f5f5f5` canvas
- Border: `1px solid #e7e5e4`
- Border-radius: 16px (xl) for feature cards, 24px (xxl) for orb cards
- Hover shadow: `0 4px 16px rgba(0,0,0,0.04)` only — no colored glow

**Gradient Orbs (atmospheric decoration only):**
- Soft `radial-gradient` blobs using `gradient-*` tokens
- Position: `absolute`, behind content, `pointer-events: none`
- Never contain content, never used as button fills or card backgrounds
- Reduce size on mobile but never disappear

## Spacing

Section padding: 96px | Cards: 24–32px | Gaps inside grids: 16–24px | Base unit: 4px

## react-flow Specific Rules

- Node fill colors (gradient palette used for node type differentiation inside DAG):
  - `premise`    → `#a8c8e8` (sky) + Inter 14px ink text
  - `assumption` → `#c8b8e0` (lavender) + Inter 14px ink text
  - `conclusion` → `#a7e5d3` (mint) + Inter 14px ink text, slightly larger
  - `fallacy`    → `#f4c5a8` (peach) + ⚠ icon + Inter 14px ink text
- Node border: `1px #e7e5e4`, `border-radius: 12px`
- Edges: `#d6d3d1` (hairline-strong), 1.5px stroke, animated dash on hover
- Graph background: `#fafafa` (canvas-soft) — not white, not dark
- Build-up animation: premises fade in (150ms stagger each) → edges draw in → conclusion fades in last

## Layout

- Max content width: 1200px, centered
- App layout: left panel (WorkspaceInput 40%) | right panel (GraphCanvas 60%) on desktop; stacked on mobile
- FallacyPanel: slides in from right, overlays GraphCanvas

## React & TypeScript Rules

- Functional components only. Named exports only (except `App.tsx`).
- No Redux/Zustand — React state only
- No React Router — single page, no routing
- No Axios — native `fetch` in `hooks/useExtraction.ts` only
- Types in `src/types/graph.ts` mirror Pydantic models exactly

## Accessibility

- All CTAs: min 40px height (WCAG AA touch target)
- Graph nodes: `aria-label` with node text content
- Color is never the only differentiator — node type also shown as text label
