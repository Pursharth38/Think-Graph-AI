---
paths:
  - "backend/**/*.py"
---

# Backend & API Conventions

## Gemini API Usage

- Model: `gemini-1.5-flash` only
- Always set `responseMimeType: 'application/json'` in `generation_config`
- System prompt (schema + few-shot examples) passed as `system_instruction`
- Cap retries at 2. On failure return degraded response: premises/conclusion only

## FastAPI Conventions

- All endpoints return Pydantic models, not raw dicts
- Enable CORS for `http://localhost:5173` in `main.py`
- One router file: `routers/extraction.py` only

## What Not To Import

- No spaCy, no NLTK, no transformers
- No SQLAlchemy, no databases, no ORM
- No Celery, no Redis, no background tasks
