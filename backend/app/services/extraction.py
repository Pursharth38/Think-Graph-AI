"""
Extraction service: source_text -> AnnotatedArgument.

Pipeline:
  1. Build a Gemini request (system_instruction = cached extraction prompt,
     responseMimeType = 'application/json').
  2. Call the model, parse the JSON, validate against the LOCKED Pydantic schema
     (AnnotatedArgument / ArgumentGraph in app.models.graph).
  3. Retry up to MAX_RETRIES times if the call fails or the payload does not validate.
     On the retry we feed the validation error back to the model so it can self-correct.
  4. If every attempt fails, return a DEGRADED response: premises + conclusion only,
     no assumptions / edges / fallacy layer. This keeps /extract resilient.

Fallacy classification is NOT done here. `graph.fallacies` is always [] coming out of
this service; the fallacy-backend service enriches it downstream (see annotate_fallacies
integration hook in app.routers.extraction).

GEMINI_API_KEY is read from os.environ (loaded from .env via python-dotenv). It is never
hardcoded. If the key is missing we go straight to the degraded path.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from app.models.graph import (
    AnnotatedArgument,
    ArgumentGraph,
    Node,
    NodeType,
)
from app.services.prompt import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger("thinkgraph.extraction")

MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 2  # total attempts = 1 + MAX_RETRIES


class ExtractionError(Exception):
    """Raised when extraction cannot produce a valid graph (caller may degrade)."""


@dataclass
class ExtractionResult:
    """Outcome of an extraction attempt.

    `degraded` is reported authoritatively by this service — it is True exactly
    when we fell back to build_degraded_response (model failure / empty input),
    never inferred from graph shape. Callers (the /extract router) must read
    this flag rather than re-deriving it, so a genuine minimal-but-valid
    extraction is not mistaken for a fallback.
    """

    annotated: AnnotatedArgument
    degraded: bool


# ---------------------------------------------------------------------------
# Gemini client (lazily configured so importing this module never requires a key)
# ---------------------------------------------------------------------------


def _get_model(system_instruction: str):
    """
    Build a configured Gemini model. Imported lazily so test environments without
    the SDK / key can still import this module and exercise the parsing/validation
    and degraded-response logic via dependency injection.
    """
    import google.generativeai as genai  # local import on purpose

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ExtractionError("GEMINI_API_KEY is not set in the environment.")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_instruction,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )


def _default_generate(source_text: str, repair_hint: Optional[str] = None) -> str:
    """
    Default Gemini caller. Returns the raw JSON text from the model.

    `repair_hint` (set on retries) carries the previous validation error so the model
    can self-correct.
    """
    model = _get_model(EXTRACTION_SYSTEM_PROMPT)
    user_parts = [
        "Extract the argument graph for the following text.\n\n"
        f"SOURCE_TEXT:\n{source_text}"
    ]
    if repair_hint:
        user_parts.append(
            "\n\nYour previous output was rejected with this error. Fix it and return "
            "only the corrected JSON object:\n" + repair_hint
        )
    response = model.generate_content("".join(user_parts))
    return response.text


# ---------------------------------------------------------------------------
# Parsing / validation
# ---------------------------------------------------------------------------


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        # remove leading ```json / ``` and trailing ```
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _parse_and_validate(raw: str, source_text: str) -> AnnotatedArgument:
    """
    Parse model JSON into an AnnotatedArgument. Tolerates two shapes:
      - the full {"source_text": ..., "graph": {...}} wrapper, or
      - a bare graph object (we wrap it ourselves).
    Always overrides source_text with the caller's exact input so spans stay aligned.
    """
    payload = json.loads(_strip_code_fences(raw))

    if isinstance(payload, dict) and "graph" in payload:
        graph_payload = payload["graph"]
    else:
        graph_payload = payload

    graph = ArgumentGraph.model_validate(graph_payload)
    # Fallacy layer is owned by a separate service; never trust model-supplied fallacies.
    graph.fallacies = []
    return AnnotatedArgument(source_text=source_text, graph=graph)


# ---------------------------------------------------------------------------
# Degraded fallback
# ---------------------------------------------------------------------------


def build_degraded_response(source_text: str) -> AnnotatedArgument:
    """
    Minimal, schema-valid response used when extraction fails after all retries.

    Treats the whole text as a single premise supporting a (text-equal) conclusion.
    No assumptions, no fallacy layer. The frontend can still render *something*.
    """
    text = source_text.strip()
    end = len(source_text)
    premise = Node(
        id="P1",
        text=text or "(empty input)",
        type=NodeType.premise,
        span=(0, end) if text else None,
        implicit=not bool(text),
    )
    conclusion = Node(
        id="C1",
        text=text or "(could not extract a conclusion)",
        type=NodeType.conclusion,
        span=None,
        implicit=True,
    )
    graph = ArgumentGraph(
        premises=[premise],
        assumptions=[],
        conclusion=conclusion,
        sub_conclusions=[],
        counter_premises=[],
        edges=[],
        fallacies=[],
        argument_type=None,
        discourse_markers=[],
    )
    return AnnotatedArgument(source_text=source_text, graph=graph)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_argument(
    source_text: str,
    *,
    generate=_default_generate,
    max_retries: int = MAX_RETRIES,
) -> ExtractionResult:
    """
    Extract an argument graph from source_text.

    `generate` is injectable (defaults to the real Gemini caller) so tests can supply a
    mock without touching the network. It takes (source_text, repair_hint) and returns
    raw JSON text.

    Returns an ExtractionResult carrying the AnnotatedArgument and an authoritative
    `degraded` flag. Never raises on extraction failure: falls back to
    build_degraded_response with degraded=True.
    """
    if not source_text or not source_text.strip():
        return ExtractionResult(build_degraded_response(source_text), degraded=True)

    repair_hint: Optional[str] = None
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            raw = generate(source_text, repair_hint)
            return ExtractionResult(_parse_and_validate(raw, source_text), degraded=False)
        except (json.JSONDecodeError, ValidationError, ValueError, ExtractionError) as exc:
            last_error = exc
            repair_hint = str(exc)[:1500]
            logger.warning(
                "Extraction attempt %d/%d failed: %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
        except Exception as exc:  # noqa: BLE001 - SDK/network errors
            last_error = exc
            repair_hint = None  # don't feed opaque SDK errors back to the model
            logger.warning(
                "Extraction attempt %d/%d errored: %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )

    logger.error("Extraction failed after %d attempts; degrading. Last error: %s",
                 max_retries + 1, last_error)
    return ExtractionResult(build_degraded_response(source_text), degraded=True)
