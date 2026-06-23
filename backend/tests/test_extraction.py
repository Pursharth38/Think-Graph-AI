"""
Tests for the extraction service, graph_builder, and /extract endpoint.

All Gemini calls are mocked — no network, no API key required. Real argument graphs
from backend/tests/gold_examples/*.json are used as the "model output" so we exercise
the parsing/validation path against realistic, schema-conformant data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.graph import AnnotatedArgument, ArgumentGraph
from app.routers import extraction as router_mod
from app.services import extraction
from app.services.extraction import ExtractionResult
from app.services.graph_builder import build_react_flow

GOLD_DIR = Path(__file__).parent / "gold_examples"
GOLD_FILES = sorted(GOLD_DIR.glob("ex_*.json"))


def _load_gold(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Gold fixtures are themselves schema-valid (sanity check on our reading of the contract)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", GOLD_FILES, ids=lambda p: p.stem)
def test_gold_examples_validate(path: Path):
    data = _load_gold(path)
    annotated = AnnotatedArgument.model_validate(data)
    assert annotated.graph.conclusion.id == "C1"


# ---------------------------------------------------------------------------
# extract_argument: happy path with a mocked Gemini generate()
# ---------------------------------------------------------------------------


def _mock_generate_from_gold(path: Path):
    gold = _load_gold(path)

    def _generate(source_text: str, repair_hint=None) -> str:
        # Return the gold graph as the "model" JSON output.
        return json.dumps(gold)

    return _generate, gold


@pytest.mark.parametrize("path", GOLD_FILES, ids=lambda p: p.stem)
def test_extract_argument_parses_gold(path: Path):
    generate, gold = _mock_generate_from_gold(path)
    result = extraction.extract_argument(gold["source_text"], generate=generate)
    assert isinstance(result, ExtractionResult)
    assert result.degraded is False  # a parsed gold graph is never degraded
    annotated = result.annotated
    assert annotated.source_text == gold["source_text"]
    assert annotated.graph.conclusion.text == gold["graph"]["conclusion"]["text"]
    # Extraction service must NEVER populate fallacies (separate service owns them).
    assert annotated.graph.fallacies == []


def test_extract_accepts_bare_graph_object():
    """Model may return just the graph (no source_text/graph wrapper)."""
    gold = _load_gold(GOLD_FILES[0])

    def generate(source_text, repair_hint=None):
        return json.dumps(gold["graph"])

    result = extraction.extract_argument(gold["source_text"], generate=generate)
    assert result.annotated.graph.conclusion.id == "C1"


def test_extract_strips_code_fences():
    gold = _load_gold(GOLD_FILES[0])

    def generate(source_text, repair_hint=None):
        return "```json\n" + json.dumps(gold) + "\n```"

    result = extraction.extract_argument(gold["source_text"], generate=generate)
    assert result.annotated.graph.conclusion.id == "C1"


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


def test_retry_then_succeed():
    gold = _load_gold(GOLD_FILES[0])
    calls = {"n": 0}

    def generate(source_text, repair_hint=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not valid json {{{"
        return json.dumps(gold)

    result = extraction.extract_argument(gold["source_text"], generate=generate)
    assert calls["n"] == 2
    assert result.degraded is False
    assert result.annotated.graph.conclusion.id == "C1"


def test_retry_passes_repair_hint_on_second_attempt():
    gold = _load_gold(GOLD_FILES[0])
    seen_hints = []

    def generate(source_text, repair_hint=None):
        seen_hints.append(repair_hint)
        if len(seen_hints) == 1:
            return "{ broken"
        return json.dumps(gold)

    extraction.extract_argument(gold["source_text"], generate=generate)
    assert seen_hints[0] is None
    assert seen_hints[1] is not None  # repair hint fed back on retry


def test_caps_at_two_retries_then_degrades():
    calls = {"n": 0}

    def generate(source_text, repair_hint=None):
        calls["n"] += 1
        return "always invalid"

    src = "Some argument text that cannot be parsed."
    result = extraction.extract_argument(src, generate=generate)
    # 1 initial + 2 retries = 3 total attempts.
    assert calls["n"] == 3
    # Authoritative degraded flag + degraded response shape.
    assert result.degraded is True
    annotated = result.annotated
    assert len(annotated.graph.premises) == 1
    assert annotated.graph.edges == []
    assert annotated.graph.conclusion.implicit is True
    assert annotated.source_text == src


def test_validation_error_triggers_degrade():
    """Well-formed JSON that violates the schema (edge to unknown node) -> degrade."""

    def generate(source_text, repair_hint=None):
        return json.dumps(
            {
                "premises": [
                    {"id": "P1", "text": "x", "type": "premise", "span": [0, 1], "implicit": False}
                ],
                "assumptions": [],
                "conclusion": {"id": "C1", "text": "y", "type": "conclusion", "span": None, "implicit": True},
                "sub_conclusions": [],
                "counter_premises": [],
                "edges": [{"from": "P9", "to_node": "C1", "edge_type": "supports"}],
                "fallacies": [],
                "argument_type": None,
                "discourse_markers": [],
            }
        )

    result = extraction.extract_argument("text", generate=generate)
    # Schema rejects unknown node -> all attempts fail -> degraded.
    assert result.degraded is True
    assert len(result.annotated.graph.premises) == 1
    assert result.annotated.graph.conclusion.implicit is True


def test_empty_input_degrades_without_calling_model():
    called = {"n": 0}

    def generate(source_text, repair_hint=None):
        called["n"] += 1
        return "{}"

    result = extraction.extract_argument("   ", generate=generate)
    assert called["n"] == 0
    assert result.degraded is True
    assert len(result.annotated.graph.premises) == 1


# ---------------------------------------------------------------------------
# graph_builder -> react-flow
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", GOLD_FILES, ids=lambda p: p.stem)
def test_build_react_flow_shape(path: Path):
    gold = _load_gold(path)
    graph = ArgumentGraph.model_validate(gold["graph"])
    rf = build_react_flow(graph)

    node_ids = {n["id"] for n in rf["nodes"]}
    assert "C1" in node_ids
    for n in rf["nodes"]:
        assert "position" in n and "x" in n["position"] and "y" in n["position"]
        assert n["data"]["label"]

    # Every react-flow edge endpoint must be a declared node.
    for e in rf["edges"]:
        assert e["source"] in node_ids
        assert e["target"] in node_ids
        assert e["id"]


def test_react_flow_expands_multi_source_edges():
    gold = _load_gold(GOLD_DIR / "ex_03.json")  # has ["P1","P2"] -> C1
    graph = ArgumentGraph.model_validate(gold["graph"])
    rf = build_react_flow(graph)
    targets = [(e["source"], e["target"]) for e in rf["edges"]]
    assert ("P1", "C1") in targets
    assert ("P2", "C1") in targets


# ---------------------------------------------------------------------------
# /extract endpoint (FastAPI), Gemini call patched out
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    gold = _load_gold(GOLD_FILES[0])

    def fake_extract_argument(source_text, **kwargs):
        annotated = AnnotatedArgument.model_validate(
            {"source_text": source_text, "graph": gold["graph"]}
        )
        return ExtractionResult(annotated, degraded=False)

    monkeypatch.setattr(router_mod.extraction, "extract_argument", fake_extract_argument)
    router_mod.set_fallacy_annotator(None)
    return TestClient(app)


def test_extract_endpoint_returns_graph_and_react_flow(client):
    resp = client.post("/extract", json={"source_text": "Hello argument."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source_text"] == "Hello argument."
    assert body["graph"]["conclusion"]["id"] == "C1"
    # Edge serialised with the "from" alias, not "from_nodes".
    assert "from" in body["graph"]["edges"][0]
    assert body["react_flow"] is not None
    assert body["degraded"] is False


def test_extract_endpoint_can_skip_react_flow(client):
    resp = client.post(
        "/extract", json={"source_text": "Hello.", "include_react_flow": False}
    )
    assert resp.status_code == 200
    assert resp.json()["react_flow"] is None


def test_extract_endpoint_rejects_empty(client):
    resp = client.post("/extract", json={"source_text": ""})
    assert resp.status_code == 422  # min_length=1 validation


def test_fallacy_annotator_hook_is_invoked(client):
    """The fallacy-backend integration point populates graph.fallacies."""

    def annotator(arg: AnnotatedArgument) -> AnnotatedArgument:
        arg.graph.fallacies = [
            {
                "node_ids": ["C1"],
                "fallacy_type": "hasty_generalization",
                "explanation": "test",
                "confidence": 0.9,
            }
        ]
        # re-validate to mimic a real annotator returning a clean object
        return AnnotatedArgument.model_validate(arg.model_dump(by_alias=True))

    router_mod.set_fallacy_annotator(annotator)
    try:
        resp = client.post("/extract", json={"source_text": "Hello."})
        body = resp.json()
        assert body["graph"]["fallacies"][0]["fallacy_type"] == "hasty_generalization"
    finally:
        router_mod.set_fallacy_annotator(None)


def test_minimal_valid_extraction_is_not_flagged_degraded(monkeypatch):
    """Regression: a genuine one-premise / implicit-conclusion / no-edge graph used to
    match the router's old shape heuristic and was wrongly marked degraded — which also
    skipped the fallacy layer. With the authoritative flag it stays degraded=False and
    is still fallacy-annotated."""
    minimal = AnnotatedArgument.model_validate(
        {
            "source_text": "All swans I have seen are white, so all swans are white.",
            "graph": {
                "premises": [
                    {"id": "P1", "text": "All swans I have seen are white.",
                     "type": "premise", "span": None, "implicit": False}
                ],
                "assumptions": [],
                "conclusion": {"id": "C1", "text": "All swans are white.",
                               "type": "conclusion", "span": None, "implicit": True},
                "edges": [],
            },
        }
    )

    def fake_extract_argument(source_text, **kwargs):
        # The service parsed a valid graph -> NOT degraded, even though its shape
        # (1 premise, implicit conclusion, no edges, no assumptions) matches the old heuristic.
        return ExtractionResult(minimal, degraded=False)

    monkeypatch.setattr(router_mod.extraction, "extract_argument", fake_extract_argument)

    annotator_calls = {"n": 0}

    def annotator(arg: AnnotatedArgument) -> AnnotatedArgument:
        annotator_calls["n"] += 1
        arg.graph.fallacies = [
            {"node_ids": ["P1", "C1"], "fallacy_type": "hasty_generalization",
             "explanation": "Generalizing from a limited sample of swans.", "confidence": 0.8}
        ]
        return AnnotatedArgument.model_validate(arg.model_dump(by_alias=True))

    router_mod.set_fallacy_annotator(annotator)
    try:
        resp = TestClient(app).post("/extract", json={"source_text": minimal.source_text})
        body = resp.json()
        assert body["degraded"] is False           # not mislabeled
        assert annotator_calls["n"] == 1            # fallacy layer was NOT skipped
        assert body["graph"]["fallacies"][0]["fallacy_type"] == "hasty_generalization"
    finally:
        router_mod.set_fallacy_annotator(None)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
