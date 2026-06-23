# OWNED BY: fallacy-backend agent.
"""
ThinkGraph AI — Two-Tier Fallacy Classifier
============================================

Public entrypoints::

    from app.services.fallacy import classify_fallacies, annotate_fallacies

    # 1. Low-level: source_text + graph -> list[Fallacy]
    fallacies = classify_fallacies(source_text, graph)

    # 2. Router seam: AnnotatedArgument -> AnnotatedArgument (with .graph.fallacies)
    #    Matches the FallacyAnnotator type the /extract router expects:
    #        from app.routers.extraction import set_fallacy_annotator
    #        set_fallacy_annotator(annotate_fallacies)

The ``/extract`` endpoint (owned by the extraction-backend agent) registers an
annotator via ``set_fallacy_annotator``. We provide :func:`annotate_fallacies`
with exactly the expected ``AnnotatedArgument -> AnnotatedArgument`` signature;
it calls :func:`classify_fallacies` under the hood and returns the same
argument with ``graph.fallacies`` populated.

Two tiers
---------
**Tier 1 — structural (cheap, no LLM).**
    Detect ``circular_reasoning`` directly from the DAG: if the support/enable
    edges contain a directed cycle, the argument literally supports its own
    premise. This is deterministic and runs first.

**Tier 2 — LLM few-shot (semantic).**
    Everything else (affirming/denying conditionals, hasty generalization,
    equivocation, false dichotomy, slippery slope, the semantic flavour of
    circular reasoning, straw man, ad hominem, tu quoque) is a meaning-level
    judgement, so we hand the argument plus a curated few-shot bank
    (:mod:`data.fallacy_examples`) to Gemini ``gemini-2.5-flash`` in JSON mode.

Per project rules (CLAUDE.md): model is ``gemini-2.5-flash`` only,
``responseMimeType='application/json'``, system prompt passed as
``system_instruction`` (implicitly cached), at most 2 retries, and on hard
failure we degrade gracefully — return Tier-1 results only rather than raise,
so the endpoint can still serve premises/conclusion without a fallacy layer.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Optional

from app.models.graph import (
    AnnotatedArgument,
    ArgumentGraph,
    EdgeType,
    Fallacy,
    FallacyType,
)
from data.fallacy_examples import (
    NEGATIVE_EXAMPLE,
    TAXONOMY,
    iter_examples,
)

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 2

# Edge types that express "X gives reason/mechanism for Y" — the relations
# whose cycles indicate circular support. 'undermines' is an attack and
# 'requires' is a necessary-condition link, so they are excluded from the
# circularity check.
_SUPPORT_EDGE_TYPES = {EdgeType.supports, EdgeType.enables}


# ===========================================================================
# Public API
# ===========================================================================


def classify_fallacies(
    source_text: str,
    graph: ArgumentGraph,
    *,
    model: Optional[Any] = None,
) -> list[Fallacy]:
    """Detect logical fallacies in an already-extracted argument.

    Parameters
    ----------
    source_text:
        The original argument paragraph (verbatim exam text).
    graph:
        The structural :class:`ArgumentGraph` produced by the extractor.
        Only its nodes and edges are read; ``graph.fallacies`` is ignored on
        input and is what this function is meant to populate downstream.
    model:
        Optional pre-built Gemini model object. Primarily a test seam — pass a
        fake with a ``.generate_content(prompt)`` method to avoid a network
        call. When ``None`` we lazily construct the real client.

    Returns
    -------
    list[Fallacy]
        Validated :class:`Fallacy` objects. Empty list means the argument is
        structurally sound (the schema explicitly allows empty fallacy lists,
        e.g. Type E constraint arguments). Never raises on LLM failure — it
        degrades to Tier-1 (structural) results only.
    """
    node_ids = _collect_node_ids(graph)

    # ---- Tier 1: structural circular-reasoning detection ----------------
    tier1 = _detect_circular_reasoning(graph)
    found_types = {f.fallacy_type for f in tier1}

    # ---- Tier 2: LLM few-shot classification ----------------------------
    try:
        tier2_raw = _llm_classify(source_text, graph, model=model)
    except Exception as exc:  # degrade gracefully — never break /extract
        logger.warning("Tier-2 fallacy LLM failed, degrading to Tier-1 only: %s", exc)
        tier2_raw = []

    tier2 = _validate_fallacies(tier2_raw, valid_node_ids=node_ids)

    # ---- Merge: Tier-1 wins for circular_reasoning ----------------------
    merged: list[Fallacy] = list(tier1)
    for fal in tier2:
        # Don't double-report circular reasoning the graph already proved.
        if fal.fallacy_type == FallacyType.circular_reasoning and (
            FallacyType.circular_reasoning in found_types
        ):
            continue
        merged.append(fal)
    return merged


def annotate_fallacies(
    arg: AnnotatedArgument,
    *,
    model: Optional[Any] = None,
) -> AnnotatedArgument:
    """Router-facing adapter: populate ``arg.graph.fallacies`` and return it.

    Signature matches the ``FallacyAnnotator`` type the /extract router expects
    (``AnnotatedArgument -> AnnotatedArgument``). Register it with::

        from app.routers.extraction import set_fallacy_annotator
        from app.services.fallacy import annotate_fallacies
        set_fallacy_annotator(annotate_fallacies)

    Returns the SAME argument with its fallacy layer filled in. Never raises:
    on any failure it logs and returns the argument with an empty fallacy list,
    so the /extract endpoint always succeeds.
    """
    try:
        fallacies = classify_fallacies(arg.source_text, arg.graph, model=model)
        arg.graph.fallacies = fallacies
    except Exception as exc:  # noqa: BLE001 — never break /extract
        logger.warning("annotate_fallacies failed; leaving fallacies empty: %s", exc)
        arg.graph.fallacies = []
    return arg


# ===========================================================================
# Tier 1 — structural
# ===========================================================================


def _collect_node_ids(graph: ArgumentGraph) -> set[str]:
    """Every declared node id in the graph (for fallacy validation)."""
    ids = {graph.conclusion.id}
    for bucket in (
        graph.premises,
        graph.assumptions,
        graph.sub_conclusions,
        graph.counter_premises,
    ):
        ids.update(n.id for n in bucket)
    return ids


def _detect_circular_reasoning(graph: ArgumentGraph) -> list[Fallacy]:
    """Tier-1: report circular_reasoning if support edges form a cycle.

    Builds a directed adjacency over support/enable edges (source -> target)
    and runs a DFS cycle search. A cycle means some node ultimately supports
    one of its own supporters, i.e. the argument leans on its conclusion to
    justify a premise.
    """
    adj: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.edge_type not in _SUPPORT_EDGE_TYPES:
            continue
        for src in edge.from_nodes:
            adj.setdefault(src, []).append(edge.to_node)

    cycle = _find_cycle(adj)
    if not cycle:
        return []

    cycle_label = " -> ".join(cycle)
    return [
        Fallacy(
            node_ids=_dedupe_preserve_order(cycle),
            fallacy_type=FallacyType.circular_reasoning,
            explanation=(
                "The support edges form a directed cycle (" + cycle_label + "). "
                "These claims support one another in a loop, so the argument "
                "ultimately uses its conclusion to justify one of its own "
                "premises rather than offering independent grounds."
            ),
            confidence=0.9,
        )
    ]


def _find_cycle(adj: dict[str, list[str]]) -> list[str]:
    """Return the node ids of one directed cycle, or [] if the graph is acyclic."""
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    stack: list[str] = []

    def dfs(node: str) -> Optional[list[str]]:
        color[node] = GREY
        stack.append(node)
        for nxt in adj.get(node, []):
            state = color.get(nxt, WHITE)
            if state == GREY:
                # Back-edge: extract the cycle slice from the stack.
                idx = stack.index(nxt)
                return stack[idx:]
            if state == WHITE:
                found = dfs(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for start in list(adj.keys()):
        if color.get(start, WHITE) == WHITE:
            found = dfs(start)
            if found:
                return found
    return []


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


# ===========================================================================
# Tier 2 — LLM few-shot
# ===========================================================================

SYSTEM_INSTRUCTION = (
    "You are a logic tutor that detects formal and informal fallacies in short "
    "exam-style arguments (UCAT / OC / TSA register). You are given the original "
    "paragraph and the already-extracted argument nodes (each with a stable id and "
    "its claim text). Your job is ONLY to flag fallacies — do NOT re-extract or "
    "rename nodes.\n\n"
    "Rules:\n"
    "1. Use ONLY these fallacy_type values (snake_case): "
    + ", ".join(TAXONOMY)
    + ".\n"
    "2. Reference fallacies to the specific node ids given. node_ids must be a "
    "non-empty subset of the provided ids, naming the inference step that is "
    "flawed (usually the source premises plus the target conclusion).\n"
    "3. The explanation MUST name the actual claims/nodes involved (quote or "
    "paraphrase their content). NEVER give a generic textbook definition.\n"
    "4. confidence is a float 0.0-1.0. Use >=0.85 for unambiguous fallacies, "
    "0.5-0.85 when present but arguable, and <0.5 for latent/possible fallacies "
    "that the structure merely risks.\n"
    "5. The two conditional-logic fallacies are the most common in this domain: "
    "affirming_the_consequent (P->Q, given Q, concludes P) and "
    "denying_the_antecedent (P->Q, given not-P, concludes not-Q). Check every "
    "if/then, 'whoever', and 'whenever' rule for these.\n"
    "6. If the argument is logically valid (e.g. modus ponens/tollens, a "
    "constraint-satisfaction deduction, or sound once an assumption is granted), "
    "return an EMPTY fallacies list. Do not invent fallacies.\n"
    "7. Output STRICT JSON only, of the form "
    '{"fallacies": [{"node_ids": [...], "fallacy_type": "...", '
    '"explanation": "...", "confidence": 0.0}]}.'
)


@lru_cache(maxsize=1)
def _few_shot_prefix() -> str:
    """The static worked-example bank — identical for every request, so build it
    once and reuse. (The examples are constants in data.fallacy_examples.)"""
    parts: list[str] = [
        "Here are worked examples. Study the INPUT and the correct OUTPUT.\n"
    ]

    for i, ex in enumerate(iter_examples(), start=1):
        parts.append(f"### Example {i}")
        parts.append("INPUT:")
        parts.append(json.dumps(ex.prompt_input(), ensure_ascii=False))
        parts.append("OUTPUT:")
        parts.append(json.dumps(ex.prompt_output(), ensure_ascii=False))
        parts.append("")

    # Negative anchor — a valid argument yields an empty list.
    parts.append("### Example (valid argument — no fallacy)")
    parts.append("INPUT:")
    parts.append(
        json.dumps(
            {
                "source_text": NEGATIVE_EXAMPLE["source_text"],
                "nodes": NEGATIVE_EXAMPLE["nodes"],
            },
            ensure_ascii=False,
        )
    )
    parts.append("OUTPUT:")
    parts.append(json.dumps({"fallacies": NEGATIVE_EXAMPLE["fallacies"]}, ensure_ascii=False))
    parts.append("")
    return "\n".join(parts)


def build_prompt(source_text: str, graph: ArgumentGraph) -> str:
    """Assemble the full few-shot user prompt (cached examples + the real argument)."""
    dynamic = "\n".join(
        [
            "### Now classify this argument",
            "INPUT:",
            json.dumps(_graph_to_prompt_input(source_text, graph), ensure_ascii=False),
            "OUTPUT:",
        ]
    )
    return _few_shot_prefix() + "\n" + dynamic


def _graph_to_prompt_input(source_text: str, graph: ArgumentGraph) -> dict[str, Any]:
    """Serialise the live graph into the same shape as the few-shot inputs."""
    nodes: list[dict[str, str]] = []
    for bucket in (
        graph.premises,
        graph.assumptions,
        graph.sub_conclusions,
        graph.counter_premises,
    ):
        nodes.extend({"id": n.id, "text": n.text} for n in bucket)
    nodes.append({"id": graph.conclusion.id, "text": graph.conclusion.text})

    edges = [
        {
            "from": e.from_nodes,
            "to": e.to_node,
            "type": e.edge_type.value,
        }
        for e in graph.edges
    ]
    return {"source_text": source_text, "nodes": nodes, "edges": edges}


def _llm_classify(
    source_text: str,
    graph: ArgumentGraph,
    *,
    model: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """Call Gemini (or an injected fake) and return raw fallacy dicts."""
    client = model if model is not None else _build_model()
    prompt = build_prompt(source_text, graph)

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):  # 1 initial + MAX_RETRIES retries
        try:
            response = client.generate_content(prompt)
            text = _extract_text(response)
            data = json.loads(text)
            fallacies = data.get("fallacies", [])
            if not isinstance(fallacies, list):
                raise ValueError("'fallacies' is not a list")
            return fallacies
        except Exception as exc:  # noqa: BLE001 — retry on any parse/transport error
            last_exc = exc
            logger.info("Tier-2 attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES + 1, exc)

    assert last_exc is not None
    raise last_exc


def _build_model() -> Any:
    """Construct the real Gemini client lazily (so tests need not import it)."""
    import google.generativeai as genai  # local import: optional at test time

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config={"response_mime_type": "application/json"},
    )


def _extract_text(response: Any) -> str:
    """Pull the JSON text out of a Gemini response (or a fake)."""
    text = getattr(response, "text", None)
    if text:
        return text
    # Fallback for the candidates/parts structure.
    candidates = getattr(response, "candidates", None)
    if candidates:
        parts = getattr(candidates[0].content, "parts", [])
        if parts:
            return parts[0].text
    raise ValueError("Gemini response contained no text to parse.")


def _validate_fallacies(
    raw: list[dict[str, Any]],
    *,
    valid_node_ids: set[str],
) -> list[Fallacy]:
    """Coerce raw dicts into Fallacy objects, dropping anything malformed.

    We never let a single bad item from the model sink the whole response:
    each is validated independently, unknown node ids are filtered, and
    confidence is clamped to [0, 1]. Items that still can't validate are skipped.
    """
    out: list[Fallacy] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        node_ids = [nid for nid in item.get("node_ids", []) if nid in valid_node_ids]
        if not node_ids:
            logger.info("Dropping fallacy with no known node_ids: %r", item.get("node_ids"))
            continue

        ftype = item.get("fallacy_type")
        try:
            ftype_enum = FallacyType(ftype)
        except ValueError:
            logger.info("Dropping fallacy with unknown type: %r", ftype)
            continue

        confidence = item.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        explanation = str(item.get("explanation", "")).strip()
        if not explanation:
            explanation = (
                f"Possible {ftype_enum.value} involving "
                f"{', '.join(node_ids)} (no detailed explanation returned)."
            )

        try:
            out.append(
                Fallacy(
                    node_ids=node_ids,
                    fallacy_type=ftype_enum,
                    explanation=explanation,
                    confidence=confidence,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("Dropping un-validatable fallacy %r: %s", item, exc)
            continue
    return out
