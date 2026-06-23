# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

ThinkGraph AI takes an argument paragraph (UCAT/CLAT/TSA-style exam questions) and returns a structured JSON graph of premises, assumptions, conclusions, edges, and fallacies. It renders this as an animated interactive DAG using react-flow, then lets students click nodes to get Socratic explanations.

## Why LLM, Not NER

Logical role (premise vs assumption vs conclusion) is a **semantic** judgment, not a surface pattern. DO NOT simplify to rule-based parsing, spaCy NER, or discourse-marker heuristics — this decision is intentional and load-bearing for the project's correctness.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python) + Gemini API (`gemini-1.5-flash`, native JSON mode) |
| Frontend | React + Vite + TypeScript + Tailwind + react-flow |
| Database | **NONE** — stateless per request |
| Prompt caching | Gemini implicit caching on system prompt (identical per session) |

**Not used:** spaCy, NLTK, SQLAlchemy, PostgreSQL, practice mode, user auth, Docker, React Router, dark mode.

## Design System

Frontend uses an ElevenLabs-inspired editorial design system. Full spec at: **`docs/DESIGN.md`**

Key rules:
- Canvas: `#f5f5f5` (off-white) | Ink: `#0c0a09` (near-black)
- Display font: EB Garamond weight 300 (open-source Waldenburg substitute) — **never bold**
- Body font: Inter 400 (body) / 500 (labels, buttons)
- CTAs: pill shape (`border-radius: 9999px`), ink background only
- Atmospheric gradient orbs (mint/peach/lavender/sky/rose) for decoration only — never as button fills
- Cards: `border-radius: 16px`, white on off-white canvas, `1px #e7e5e4` border
- **NO** saturated accent colors. **NO** dark mode. **NO** routing (single-page app).

## Critical File Ownership Rules

| File | Owner | All Others |
|---|---|---|
| `docs/argument-patterns.md` | `question-analyzer` agent | READ ONLY |
| `backend/app/models/graph.py` | `schema-designer` agent | READ ONLY |
| `backend/data/fallacy_examples.py` | `fallacy-backend` agent | READ ONLY |
| `backend/tests/gold_examples/` | `schema-designer` agent | READ ONLY |
| `docs/DESIGN.md` | Human only | READ ONLY |

**schema-designer** commits `graph.py` and locks it — no agent modifies it without explicit human approval.

## Dev Commands

```bash
# Backend (port 8000)
cd backend && uvicorn app.main:app --reload

# Frontend (port 5173)
cd frontend && npm run dev

# Tests
cd backend && pytest tests/ -v

# Single test file
cd backend && pytest tests/test_extraction.py -v
```

## Gemini API

- `GEMINI_API_KEY` comes from `.env` (via `os.environ`) — never hardcode it
- Model: `gemini-2.5-flash` only
- Always set `responseMimeType: 'application/json'` in `generation_config`
- System prompt passed as `system_instruction` — cached across the session
- Retry cap: 2 retries. On failure → degraded response (premises/conclusion only, no fallacy layer)

## Extraction JSON Schema (the contract)

```json
{
  "premises":    [{"id": "P1", "text": "...", "span": [start, end]}],
  "assumptions": [{"id": "A1", "text": "...", "implicit": true}],
  "conclusion":  {"id": "C1", "text": "...", "span": [start, end]},
  "edges":       [{"from": ["P1", "P2"], "to": "C1", "type": "supports"}],
  "fallacies":   [{"type": "...", "involved_nodes": ["P1"], "explanation": "...", "confidence": 0.0}]
}
```

Pydantic schema lives at `backend/app/models/graph.py`. Do not modify it without also updating the gold examples.

## Agent Execution Order

```
Phase 0:  question-analyzer  →  schema-designer   (sequential)
Phase 1:  extraction-backend ∥ fallacy-backend    (parallel)
Phase 2:  graph-frontend                          (after both backends done)
```

## Build Phase Gates

Use `/code-review` at each phase boundary before the next agent builds on top. Use `/verify` after each phase to confirm the feature works in the real app, not just tests.
