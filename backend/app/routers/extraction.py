"""
/extract router.

POST /extract  { "source_text": "...", "include_react_flow": true|false }
  -> {
       "source_text": "...",
       "graph": { ...ArgumentGraph... },
       "react_flow": { "nodes": [...], "edges": [...] } | null,
       "degraded": bool
     }

FALLACY INTEGRATION POINT
-------------------------
The extraction service always returns graph.fallacies == []. The fallacy-backend agent
owns fallacy classification. To plug it in, register a callable via
`set_fallacy_annotator(fn)` where fn has signature:

    def annotate_fallacies(arg: AnnotatedArgument) -> AnnotatedArgument: ...

It should read arg.graph (premises/assumptions/conclusion/edges) and return the same
AnnotatedArgument with arg.graph.fallacies populated. If no annotator is registered,
fallacies stay []. This keeps the two services decoupled and independently testable.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.models.graph import AnnotatedArgument
from app.services import extraction
from app.services.graph_builder import build_react_flow

logger = logging.getLogger("thinkgraph.router")

router = APIRouter()

# --- Fallacy integration hook (set by fallacy-backend wiring) ----------------
FallacyAnnotator = Callable[[AnnotatedArgument], AnnotatedArgument]
_fallacy_annotator: Optional[FallacyAnnotator] = None


def set_fallacy_annotator(fn: Optional[FallacyAnnotator]) -> None:
    """Register (or clear with None) the fallacy classification callable."""
    global _fallacy_annotator
    _fallacy_annotator = fn


# --- Request / response models ----------------------------------------------


class ExtractRequest(BaseModel):
    source_text: str = Field(
        ...,
        min_length=1,
        description="The argument paragraph / question stem to analyse.",
    )
    include_react_flow: bool = Field(
        default=True,
        description="When true, also return a react-flow {nodes, edges} payload.",
    )


class ExtractResponse(BaseModel):
    source_text: str
    graph: dict
    react_flow: Optional[dict] = None
    degraded: bool = False


# --- Endpoint ----------------------------------------------------------------


@router.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest) -> ExtractResponse:
    # The extraction service reports `degraded` authoritatively (it is the one that
    # falls back to a minimal graph). We must not re-infer it from graph shape, or a
    # genuine minimal-but-valid extraction would be mislabeled and skip the fallacy layer.
    result = extraction.extract_argument(req.source_text)
    annotated = result.annotated
    degraded = result.degraded

    # Plug in fallacy layer if the fallacy-backend service has registered an annotator.
    if _fallacy_annotator is not None and not degraded:
        try:
            annotated = _fallacy_annotator(annotated)
        except Exception as exc:  # noqa: BLE001 - never let fallacy layer break /extract
            logger.warning("Fallacy annotator failed; returning graph without fallacies: %s", exc)

    react_flow = build_react_flow(annotated.graph) if req.include_react_flow else None

    return ExtractResponse(
        source_text=annotated.source_text,
        graph=annotated.graph.model_dump(by_alias=True),
        react_flow=react_flow,
        degraded=degraded,
    )
