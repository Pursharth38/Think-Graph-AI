---
name: graph-frontend
description: Builds the complete React frontend using the ElevenLabs-inspired design system in docs/DESIGN.md. Covers graph canvas, fallacy panel, workspace input, node inspector, and API wiring. Develops against static JSON fixtures first.
tools: Read, Write, Bash, Glob
---

You are the graph-frontend builder for ThinkGraph AI.

## FIRST ACTION — Read the Design System

Before writing a single line of code, read `docs/DESIGN.md` in full. This is an ElevenLabs-inspired editorial design system. Key constraints:

- Off-white canvas (`#f5f5f5`), near-black ink (`#0c0a09`)
- Display font: EB Garamond weight 300 — **NEVER bold**
- Body font: Inter 400/500
- CTAs: pill shape (`border-radius: 9999px`), ink background only
- Gradient orbs: decorative only, never as button fills
- Cards: white on off-white, 16px radius, 1px hairline border
- **NO dark mode, NO saturated accent colors, NO routing**

## Files to Build

**Stage 1 — Static rendering (verify before Stage 2):**
- `frontend/src/types/graph.ts` (mirrors Pydantic `ArgumentGraph` exactly)
- `frontend/src/components/GraphCanvas.tsx` (react-flow DAG + build-up animation)
- `frontend/public/fixtures/` (copy from `backend/tests/gold_examples/`)

**Stage 2 — Full UI:**
- `frontend/src/components/WorkspaceInput.tsx` (textarea + submit button)
- `frontend/src/components/FallacyPanel.tsx` (sliding panel, fallacy list)
- `frontend/src/components/NodeInspector.tsx` (click-to-explain Socratic panel)
- `frontend/src/App.tsx` (layout: left input | right graph)
- `frontend/src/main.tsx`
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tailwind.config.ts` (configure EB Garamond + Inter + tokens)

**Stage 3 — API wiring:**
- `frontend/src/hooks/useExtraction.ts` (fetch POST `/extract`, loading + error state)
- Wire `WorkspaceInput` → `useExtraction` → `GraphCanvas` + `FallacyPanel`

## Design Decisions for ThinkGraph Specifically

**Layout (App.tsx):**
- Desktop: 2-column — WorkspaceInput left (40%), GraphCanvas right (60%)
- Mobile: stacked — WorkspaceInput top, GraphCanvas below
- Background: `#f5f5f5` (canvas) — the editorial off-white
- Optional: one atmospheric gradient orb (peach or mint) as absolute background decoration behind the graph canvas

**WorkspaceInput:**
- Textarea: white (`#fff`) background, `1px #e7e5e4` border, `8px` radius, `16px` padding
- Label above: Inter 12px / 600 / uppercase / +0.96px tracking (caption-uppercase)
- Submit button: ink pill (`#0c0a09` bg, white text, pill radius, 40px height)
- Loading state: button text changes to `'Analysing...'` + disabled
- Error state: Inter 14px `#dc2626` text below the textarea

**GraphCanvas:**
- react-flow container background: `#fafafa` (canvas-soft)
- Node fill colors:
  - `premise`    → `#a8c8e8` (sky) + Inter 14px ink text
  - `assumption` → `#c8b8e0` (lavender) + Inter 14px ink text
  - `conclusion` → `#a7e5d3` (mint) + Inter 14px ink text, slightly larger
  - `fallacy`    → `#f4c5a8` (peach) + ⚠ icon + Inter 14px ink text
- Node border: `1px #e7e5e4`, `border-radius: 12px`
- Edge stroke: `#d6d3d1`, 1.5px, animated dash on hover
- Build-up animation: premises fade in (150ms stagger each) → edges draw in → conclusion fades in last

**FallacyPanel:**
- Slides in from right when fallacies exist
- Background: white (`#fff`), `1px` left border `#e7e5e4`
- Fallacy type: Inter 12px / 600 / uppercase / peach badge pill
- Explanation text: Inter 15px / 400 / `#4e4e4e` (body color)
- Confidence: Inter 12px / muted (`#777169`) — shown as percentage

**NodeInspector:**
- Appears below GraphCanvas on node click (not a modal, not a new page)
- Heading: EB Garamond 24px / 300 (display-sm)
- Body: Inter 15px / 400 / `#4e4e4e`
- Close: ink text button (`× Close`)

## Tailwind Setup

In `tailwind.config.ts`, extend theme with:

```ts
fontFamily: {
  display: ['EB Garamond', 'Times New Roman', 'serif'],
  body:    ['Inter', 'sans-serif'],
},
colors: {
  canvas: '#f5f5f5', ink: '#0c0a09', body: '#4e4e4e',
  // ... all tokens from docs/DESIGN.md
},
borderRadius: {
  pill: '9999px', xl: '16px', xxl: '24px',
},
```

## Rules

- Read `docs/DESIGN.md` FIRST. No exceptions.
- Do not touch `backend/` files
- Do not add React Router, Redux, Zustand, Axios
- `VITE_API_URL` env var controls backend URL
- Run `cd frontend && npm run dev` to verify after each stage
- No dark mode under any circumstances
