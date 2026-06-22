---
description: Smoke-tests the /extract endpoint against all gold examples.
argument-hint: (no arguments needed)
---

Run the extraction endpoint smoke test.

!`cd backend && pytest tests/test_extraction.py -v`

!`curl -s -X POST http://localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{"text": "All criminals deserve punishment. John committed fraud. Therefore John deserves punishment. But fraud is fine anyway."}' \
  | python3 -m json.tool`

Check: valid JSON, non-empty nodes, edges reference valid ids, fallacy confidence scores 0–1, no 422 errors.
