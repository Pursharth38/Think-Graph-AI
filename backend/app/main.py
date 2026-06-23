"""
ThinkGraph AI — FastAPI application entrypoint.

Run (dev):
    cd backend && uvicorn app.main:app --reload   # port 8000

CORS is opened for the Vite dev server at http://localhost:5173.
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import extraction as extraction_router
from app.routers.extraction import set_fallacy_annotator
from app.services.fallacy import annotate_fallacies

# Load GEMINI_API_KEY (and friends) from backend/.env into os.environ.
load_dotenv()

# Wire the fallacy classifier into the /extract pipeline. The router invokes
# this only for non-degraded graphs and guards it with try/except, so a
# fallacy-layer failure can never break extraction.
set_fallacy_annotator(annotate_fallacies)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="ThinkGraph AI — Extraction API",
    version="1.0.0",
    description="Turns an argument paragraph into a structured logical argument graph.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction_router.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
