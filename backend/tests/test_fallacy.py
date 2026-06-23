"""
Tests for the two-tier fallacy classifier (app.services.fallacy).

Gemini is never called: Tier-2 is exercised through an injected fake model
(``FakeModel``) that returns canned JSON, so no network or API key is needed.
Tier-1 (structural circular-reasoning detection) needs no model at all.
"""

from __future__ import annotations

import json

import pytest

from app.models.graph import (
    AnnotatedArgument,
    ArgumentGraph,
    EdgeType,
    Fallacy,
    FallacyType,
    Node,
    NodeType,
)
from app.services import fallacy as fallacy_svc
from data import fallacy_examples as bank


# ---------------------------------------------------------------------------
# Fakes / helpers
# ---------------------------------------------------------------------------


class FakeModel:
    """Stand-in for genai.GenerativeModel. Returns canned text, counts calls."""

    def __init__(self, responses):
        # responses: list of str (one per call). Last one repeats if exhausted.
        self._responses = list(responses)
        self.calls = 0
        self.prompts: list[str] = []

    def generate_content(self, prompt):
        self.prompts.append(prompt)
        idx = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        resp = self._responses[idx]
        if isinstance(resp, Exception):
            raise resp

        class _R:
            text = resp

        return _R()


def make_graph(
    premises=None,
    conclusion=("C1", "Some conclusion."),
    edges=None,
    assumptions=None,
    sub_conclusions=None,
) -> ArgumentGraph:
    premises = premises or [("P1", "Premise one.")]
    return ArgumentGraph(
        premises=[Node(id=i, text=t, type=NodeType.premise) for i, t in premises],
        assumptions=[
            Node(id=i, text=t, type=NodeType.assumption, implicit=True)
            for i, t in (assumptions or [])
        ],
        sub_conclusions=[
            Node(id=i, text=t, type=NodeType.sub_conclusion)
            for i, t in (sub_conclusions or [])
        ],
        conclusion=Node(id=conclusion[0], text=conclusion[1], type=NodeType.conclusion),
        edges=edges or [],
    )


# ---------------------------------------------------------------------------
# Few-shot bank integrity
# ---------------------------------------------------------------------------


def test_bank_covers_all_ten_fallacy_types():
    assert set(bank.EXAMPLES_BY_TYPE.keys()) == set(FallacyType)


def test_conditional_fallacies_have_strongest_coverage():
    ac = len(bank.EXAMPLES_BY_TYPE[FallacyType.affirming_the_consequent])
    da = len(bank.EXAMPLES_BY_TYPE[FallacyType.denying_the_antecedent])
    assert ac >= 3 and da >= 3
    # Each is at least as well-covered as any other (lower-priority) type.
    for ftype, examples in bank.EXAMPLES_BY_TYPE.items():
        if ftype in (
            FallacyType.affirming_the_consequent,
            FallacyType.denying_the_antecedent,
        ):
            continue
        assert len(examples) <= ac
        assert len(examples) <= da


def test_every_example_output_validates_as_fallacy():
    """Each few-shot OUTPUT must be a schema-valid Fallacy referencing real nodes."""
    for ex in bank.iter_examples():
        fal = Fallacy.model_validate(ex.fallacy)
        assert fal.fallacy_type == ex.fallacy_type
        assert 0.0 <= fal.confidence <= 1.0
        assert fal.explanation.strip()
        # node_ids must all be declared in that example's node skeleton.
        assert set(fal.node_ids).issubset(set(ex.nodes.keys()))


def test_priority_order_puts_conditionals_first():
    assert bank.TAXONOMY[0] == "affirming_the_consequent"
    assert bank.TAXONOMY[1] == "denying_the_antecedent"
    # First flat examples are the conditional fallacies.
    assert bank.ALL_EXAMPLES[0].fallacy_type == FallacyType.affirming_the_consequent


def test_negative_example_has_empty_fallacy_list():
    assert bank.NEGATIVE_EXAMPLE["fallacies"] == []


# ---------------------------------------------------------------------------
# Tier 1 — structural circular reasoning
# ---------------------------------------------------------------------------


def test_tier1_detects_support_cycle_without_calling_model():
    # P1 -> C1 -> P1  (a support loop)
    graph = make_graph(
        premises=[("P1", "X is true because of C1.")],
        conclusion=("C1", "C1 is true because of P1."),
        edges=[
            {"from": ["P1"], "to_node": "C1", "edge_type": "supports"},
            {"from": ["C1"], "to_node": "P1", "edge_type": "supports"},
        ],
    )
    # No model passed AND Tier-2 forced to fail -> only Tier-1 should fire.
    fake = FakeModel([RuntimeError("boom")])
    result = fallacy_svc.classify_fallacies("loop argument", graph, model=fake)
    circ = [f for f in result if f.fallacy_type == FallacyType.circular_reasoning]
    assert len(circ) == 1
    assert set(circ[0].node_ids) == {"P1", "C1"}
    assert circ[0].confidence == pytest.approx(0.9)


def test_tier1_ignores_undermines_edges():
    # A counter-style loop over 'undermines' must NOT be flagged as circular.
    graph = make_graph(
        edges=[
            {"from": ["P1"], "to_node": "C1", "edge_type": "undermines"},
            {"from": ["C1"], "to_node": "P1", "edge_type": "undermines"},
        ],
    )
    fake = FakeModel(['{"fallacies": []}'])
    result = fallacy_svc.classify_fallacies("t", graph, model=fake)
    assert not [f for f in result if f.fallacy_type == FallacyType.circular_reasoning]


def test_tier1_acyclic_graph_no_circular():
    graph = make_graph(
        premises=[("P1", "a"), ("P2", "b")],
        edges=[{"from": ["P1", "P2"], "to_node": "C1", "edge_type": "supports"}],
    )
    fake = FakeModel(['{"fallacies": []}'])
    result = fallacy_svc.classify_fallacies("t", graph, model=fake)
    assert result == []


def test_tier1_and_tier2_dont_double_report_circular():
    """If the graph cycle fires Tier-1 circular_reasoning, an LLM circular dup is dropped."""
    graph = make_graph(
        edges=[
            {"from": ["P1"], "to_node": "C1", "edge_type": "supports"},
            {"from": ["C1"], "to_node": "P1", "edge_type": "supports"},
        ],
    )
    llm_dup = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1", "C1"],
                    "fallacy_type": "circular_reasoning",
                    "explanation": "LLM also thinks this is circular.",
                    "confidence": 0.7,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm_dup]))
    circ = [f for f in result if f.fallacy_type == FallacyType.circular_reasoning]
    assert len(circ) == 1  # only the Tier-1 one survives
    assert circ[0].confidence == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Tier 2 — LLM classification (mocked)
# ---------------------------------------------------------------------------


def test_tier2_parses_affirming_the_consequent():
    graph = make_graph(
        premises=[("P1", "If stole, had opp & motive."), ("P2", "Finn had opp & motive.")],
        conclusion=("C1", "Finn stole the money."),
        edges=[{"from": ["P1", "P2"], "to_node": "C1", "edge_type": "supports"}],
    )
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1", "P2", "C1"],
                    "fallacy_type": "affirming_the_consequent",
                    "explanation": "P1 only says stealing requires opp+motive; P2/C1 affirm the consequent.",
                    "confidence": 0.93,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("Finn argument", graph, model=FakeModel([llm]))
    assert len(result) == 1
    assert result[0].fallacy_type == FallacyType.affirming_the_consequent
    assert result[0].confidence == pytest.approx(0.93)
    assert "P1" in result[0].node_ids


def test_tier2_empty_list_for_valid_argument():
    graph = make_graph()
    result = fallacy_svc.classify_fallacies("valid", graph, model=FakeModel(['{"fallacies": []}']))
    assert result == []


def test_tier2_drops_unknown_node_ids():
    graph = make_graph()  # nodes: P1, C1
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P9", "Z3"],  # none exist
                    "fallacy_type": "hasty_generalization",
                    "explanation": "refers to phantom nodes",
                    "confidence": 0.8,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm]))
    assert result == []


def test_tier2_filters_unknown_ids_but_keeps_valid_ones():
    graph = make_graph()  # P1, C1
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1", "GHOST", "C1"],
                    "fallacy_type": "false_dichotomy",
                    "explanation": "only two options offered between P1 and C1",
                    "confidence": 0.6,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm]))
    assert len(result) == 1
    assert result[0].node_ids == ["P1", "C1"]


def test_tier2_drops_unknown_fallacy_type():
    graph = make_graph()
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1"],
                    "fallacy_type": "not_a_real_fallacy",
                    "explanation": "x",
                    "confidence": 0.9,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm]))
    assert result == []


def test_tier2_clamps_out_of_range_confidence():
    graph = make_graph()
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1"],
                    "fallacy_type": "slippery_slope",
                    "explanation": "x",
                    "confidence": 1.7,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm]))
    assert result[0].confidence == pytest.approx(1.0)


def test_tier2_low_confidence_is_latent():
    graph = make_graph()
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1", "C1"],
                    "fallacy_type": "slippery_slope",
                    "explanation": "latent slope risk",
                    "confidence": 0.3,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm]))
    assert result[0].confidence < 0.5  # below 0.5 == latent/possible


def test_tier2_supplies_explanation_when_blank():
    graph = make_graph()
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1"],
                    "fallacy_type": "ad_hominem",
                    "explanation": "",
                    "confidence": 0.8,
                }
            ]
        }
    )
    result = fallacy_svc.classify_fallacies("t", graph, model=FakeModel([llm]))
    assert result[0].explanation.strip()  # never empty


# ---------------------------------------------------------------------------
# Retry / degradation behaviour
# ---------------------------------------------------------------------------


def test_retry_then_succeed():
    graph = make_graph()
    fake = FakeModel(["not json {{{", '{"fallacies": []}'])
    result = fallacy_svc.classify_fallacies("t", graph, model=fake)
    assert fake.calls == 2
    assert result == []


def test_caps_at_two_retries_then_degrades_to_tier1_only():
    # Acyclic graph -> Tier-1 yields nothing; LLM always fails -> empty, no raise.
    graph = make_graph()
    fake = FakeModel(["bad", "bad", "bad", "bad"])
    result = fallacy_svc.classify_fallacies("t", graph, model=fake)
    assert fake.calls == 3  # 1 initial + 2 retries
    assert result == []


def test_llm_failure_keeps_tier1_circular():
    graph = make_graph(
        edges=[
            {"from": ["P1"], "to_node": "C1", "edge_type": "supports"},
            {"from": ["C1"], "to_node": "P1", "edge_type": "supports"},
        ],
    )
    fake = FakeModel([RuntimeError("network down")])
    result = fallacy_svc.classify_fallacies("t", graph, model=fake)
    # Tier-2 dead, but Tier-1 circular survives.
    assert len(result) == 1
    assert result[0].fallacy_type == FallacyType.circular_reasoning


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def test_prompt_includes_examples_and_live_argument():
    graph = make_graph(conclusion=("C1", "UNIQUE_LIVE_CONCLUSION_TEXT"))
    prompt = fallacy_svc.build_prompt("source paragraph here", graph)
    assert "UNIQUE_LIVE_CONCLUSION_TEXT" in prompt
    assert "affirming_the_consequent" in prompt
    assert "Now classify this argument" in prompt
    # The first worked example should be a conditional fallacy (priority order).
    assert prompt.index("affirming_the_consequent") < prompt.index("Now classify")


def test_system_instruction_lists_full_taxonomy():
    for ftype in FallacyType:
        assert ftype.value in fallacy_svc.SYSTEM_INSTRUCTION


# ---------------------------------------------------------------------------
# Router adapter — annotate_fallacies(AnnotatedArgument) -> AnnotatedArgument
# ---------------------------------------------------------------------------


def test_annotate_fallacies_populates_graph():
    graph = make_graph(
        premises=[("P1", "If stole, opp & motive."), ("P2", "Finn had both.")],
        conclusion=("C1", "Finn stole it."),
        edges=[{"from": ["P1", "P2"], "to_node": "C1", "edge_type": "supports"}],
    )
    arg = AnnotatedArgument(source_text="Finn argument", graph=graph)
    llm = json.dumps(
        {
            "fallacies": [
                {
                    "node_ids": ["P1", "P2", "C1"],
                    "fallacy_type": "affirming_the_consequent",
                    "explanation": "affirms the consequent",
                    "confidence": 0.9,
                }
            ]
        }
    )
    out = fallacy_svc.annotate_fallacies(arg, model=FakeModel([llm]))
    assert out is arg
    assert len(out.graph.fallacies) == 1
    assert out.graph.fallacies[0].fallacy_type == FallacyType.affirming_the_consequent


def test_annotate_fallacies_never_raises_on_failure():
    graph = make_graph()
    arg = AnnotatedArgument(source_text="t", graph=graph)
    out = fallacy_svc.annotate_fallacies(arg, model=FakeModel([RuntimeError("boom")]))
    assert out.graph.fallacies == []
