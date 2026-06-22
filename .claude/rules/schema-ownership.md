# Schema & Shared File Ownership

## The Schema Contract

- `backend/app/models/graph.py` is THE data contract for the whole project
- Locked after schema-designer agent commits it
- No agent modifies it without explicit human approval

## File Ownership Table

| File | Owner Agent | All Others |
|---|---|---|
| `docs/argument-patterns.md` | question-analyzer | READ ONLY |
| `backend/app/models/graph.py` | schema-designer | READ ONLY |
| `backend/data/fallacy_examples.py` | fallacy-backend | READ ONLY |
| `tests/gold_examples/` | schema-designer | READ ONLY |
| `docs/DESIGN.md` | (you, the human) | READ ONLY |

## Statefulness Rule

- This project has NO database
- Every API endpoint must be fully stateless
- Never add session storage, ORM imports, or file-based response caching
