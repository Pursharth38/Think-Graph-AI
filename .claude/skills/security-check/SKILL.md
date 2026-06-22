---
description: Security audit before demo — API key exposure, CORS, input sanitization.
disable-model-invocation: true
---

!`grep -r 'AIza' frontend/dist/ 2>/dev/null || echo 'No API keys in build'`

!`grep -r 'GEMINI_API_KEY' backend/ | grep -v 'os.environ'`

!`grep -n 'CORSMiddleware\|allow_origins' backend/app/main.py`

!`cd backend && pip list | grep -E 'spacy|sqlalchemy|psycopg'`

Report: PASS / FAIL / WARNING per check with file:line references.
