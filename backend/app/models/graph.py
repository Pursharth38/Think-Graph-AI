# LOCKED CONTRACT — see CLAUDE.md and .claude/rules/schema-ownership.md before editing.
# No agent may modify this file without also updating backend/tests/gold_examples/.
"""
ThinkGraph AI — Core Data Models (Phase 0 schema, Agent 1)
===========================================================
Pure Pydantic v2 data contracts. NO service logic here.

Reflects findings from docs/argument-patterns.md:
  - 5 structural types (A–E)
  - sub_conclusions are first-class nodes (depth-3 nesting observed in Q20, Q17)
  - counter_premises required for Type D (pivot arguments)
  - dual-speaker dialogues may embed two ArgumentGraph mini-graphs
  - 10 fallacy types catalogued; affirming_the_consequent and denying_the_antecedent
    are by far the most frequent in this exam domain
  - ~75% of load-bearing assumptions are implicit (never stated in text)
  - Edge types extended: supports / undermines / enables / requires
    (argument-patterns.md §7.1 specifies 'enables' and 'requires' in addition to
     the basic supports/opposes pair)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    """Logical role of a node in the argument graph."""

    premise = "premise"
    """An explicitly stated supporting claim (P1, P2, …)."""

    assumption = "assumption"
    """An unstated bridging claim (A1, A2, …). ~75 % of load-bearing
    assumptions in this exam corpus are implicit."""

    conclusion = "conclusion"
    """The main claim being argued for (C1). Every ArgumentGraph has
    exactly one top-level conclusion."""

    sub_conclusion = "sub_conclusion"
    """An intermediate derived claim that acts as both the target of some
    edges and the source of others (e.g. P3 in Q20 birth-rate chain;
    SC1 in Q17 programming chain). argument-patterns.md §4.2 identifies
    depth-3 nesting that requires this node type."""

    counter_premise = "counter_premise"
    """A claim that argues *against* the main conclusion, typically
    introduced by 'however / but / yet' in Type D (pivot) arguments."""

    fallacy = "fallacy"
    """A node that represents an invalid inference step explicitly called
    out as erroneous (used in dual-speaker dialogue questions where one
    speaker's whole argument is the fallacious object)."""


class EdgeType(str, Enum):
    """Semantic relationship between argument nodes."""

    supports = "supports"
    """Source node provides positive evidence / reason for target node."""

    undermines = "undermines"
    """Source node weakens or contradicts the target node.
    Used for counter_premise → conclusion edges and for rejected
    alternative theories (e.g. poverty theory vs futsal theory in Q26)."""

    enables = "enables"
    """Source node provides the *mechanism* by which the target is possible.
    Distinguished from 'supports': an enabling edge says 'X makes Y
    possible', not merely 'X is evidence for Y'.
    Example: A1 (relaxation → study) enables C1 in Q2."""

    requires = "requires"
    """Target node is valid only if source node holds.
    Used for necessary-condition relationships, e.g. the implicit
    no-storage assumption (A1) is *required* for the wind-farm argument
    (Q8) to succeed."""


class FallacyType(str, Enum):
    """
    Taxonomy of fallacies found in this exam domain.

    Ordered by frequency (argument-patterns.md §7.2).
    affirming_the_consequent and denying_the_antecedent are the primary
    targets — each appears in ~15 % of logical-inference questions.
    """

    affirming_the_consequent = "affirming_the_consequent"
    denying_the_antecedent = "denying_the_antecedent"
    hasty_generalization = "hasty_generalization"
    equivocation = "equivocation"
    false_dichotomy = "false_dichotomy"
    slippery_slope = "slippery_slope"
    circular_reasoning = "circular_reasoning"
    straw_man = "straw_man"
    ad_hominem = "ad_hominem"
    tu_quoque = "tu_quoque"


class ArgumentType(str, Enum):
    """Structural type of the argument (argument-patterns.md §1.1)."""

    single_premise_implicit_assumption = "single_premise_implicit_assumption"
    two_premise_causal_gap = "two_premise_causal_gap"
    chain_conditional = "chain_conditional"
    counter_premise_pivot = "counter_premise_pivot"
    constraint_satisfaction = "constraint_satisfaction"


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


class Node(BaseModel):
    """A single logical unit (premise, assumption, conclusion, etc.)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(
        ...,
        description=(
            "Stable identifier. Convention: P1/P2 for premises, "
            "A1/A2 for assumptions, C1 for conclusion, "
            "SC1/SC2 for sub-conclusions, CP1 for counter-premises, "
            "F1 for fallacy nodes."
        ),
        examples=["P1", "A1", "C1", "SC1", "CP1"],
    )
    text: str = Field(
        ...,
        description="The claim or statement this node represents. "
        "For implicit assumptions, write out the bridging claim in full "
        "even though it does not appear verbatim in the source text.",
    )
    type: NodeType
    span: Optional[tuple[int, int]] = Field(
        default=None,
        description=(
            "Half-open [start, end) character offsets into source_text. "
            "None for implicit nodes (assumptions never stated in text) "
            "and for nodes inferred from context rather than quoted directly."
        ),
    )
    implicit: bool = Field(
        default=False,
        description=(
            "True when this node was never stated in the source text "
            "(i.e. it is an unstated bridging assumption). "
            "Implicit nodes always have span=None."
        ),
    )

    def model_post_init(self, __context: object) -> None:  # noqa: ANN001
        """Enforce the invariant: implicit nodes must have span=None."""
        if self.implicit and self.span is not None:
            raise ValueError(
                f"Node {self.id!r} is marked implicit=True "
                "but has a non-None span. Implicit nodes cannot have "
                "character offsets because they do not appear in the text."
            )


# ---------------------------------------------------------------------------
# Edge
# ---------------------------------------------------------------------------


class Edge(BaseModel):
    """
    A directed edge in the argument DAG.

    'from_nodes' supports multi-premise edges (convergent support), e.g.:
        P1 ∧ P2 ∧ A1 → C1  (the wind-farm argument, Q8)

    In JSON the field is serialised as "from" (alias) to match the natural
    key name. Python code should use .from_nodes.
    """

    model_config = ConfigDict(populate_by_name=True)

    # NOTE: 'from' is a Python keyword. Never construct Edge with Edge(from=...) —
    # use Edge.model_validate({"from": ..., "to_node": ...}) from JSON, or
    # Edge(from_nodes=[...], to_node=...) in Python code.
    from_nodes: list[str] = Field(
        ...,
        alias="from",
        description=(
            "List of source node IDs. Single-source edges use a one-element list. "
            "A bare string in JSON is coerced to [string] by the validator below."
        ),
        examples=[["P1"], ["P1", "P2", "A1"]],
    )

    @field_validator("from_nodes", mode="before")
    @classmethod
    def _normalise_from_nodes(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [v]
        return v  # type: ignore[return-value]
    to_node: str = Field(
        ...,
        description="ID of the target node this edge points to.",
        examples=["C1", "SC1"],
    )
    edge_type: EdgeType = Field(
        default=EdgeType.supports,
        description="Semantic relationship. Defaults to 'supports'.",
    )


# ---------------------------------------------------------------------------
# Fallacy
# ---------------------------------------------------------------------------


class Fallacy(BaseModel):
    """
    A detected logical fallacy within the argument.

    Tied to specific node IDs so the frontend can highlight exactly which
    inference step is flawed.
    """

    model_config = ConfigDict(populate_by_name=True)

    node_ids: list[str] = Field(
        ...,
        description=(
            "IDs of the nodes involved in the fallacious inference. "
            "Typically the source node(s) and the target node of the "
            "invalid edge, e.g. ['P1', 'P2', 'C_claimed']."
        ),
        min_length=1,
    )
    fallacy_type: FallacyType = Field(
        ...,
        description="Snake_case fallacy name from the FallacyType enum.",
    )
    explanation: str = Field(
        ...,
        description=(
            "Plain-language explanation tied to the actual argument. "
            "Must name the specific nodes/claims involved, not give a "
            "generic textbook definition."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Extractor confidence that this fallacy is present. "
            "0.0 = no evidence; 1.0 = certain. "
            "Values below 0.5 are 'latent' / possible fallacies."
        ),
    )


# ---------------------------------------------------------------------------
# Discourse Marker Detection Record
# ---------------------------------------------------------------------------


class DiscourseMarker(BaseModel):
    """
    A connective word/phrase detected in the source text, with its
    assigned logical role. Stored for transparency / debugging.

    argument-patterns.md §3 identifies misleading markers ('however',
    'but', 'therefore' mid-premise) that require special handling.
    """

    model_config = ConfigDict(populate_by_name=True)

    marker: str = Field(..., description="The surface string as it appears in the text.")
    span: Optional[tuple[int, int]] = Field(
        default=None,
        description="[start, end) offsets in source_text. None when the marker is implied rather than surface-level.",
    )
    assigned_role: str = Field(
        ...,
        description=(
            "The logical role assigned after disambiguation. "
            "E.g. 'conclusion_marker', 'premise_marker', "
            "'pivot_to_conclusion', 'conditional_antecedent'."
        ),
    )
    is_misleading: bool = Field(
        default=False,
        description=(
            "True when this marker's surface appearance contradicts its "
            "actual role (e.g. 'however' looking like an objection but "
            "actually introducing the target conclusion in a Type D argument)."
        ),
    )


# ---------------------------------------------------------------------------
# Top-level ArgumentGraph
# ---------------------------------------------------------------------------


class ArgumentGraph(BaseModel):
    """
    The complete logical structure of one argument paragraph or question stem.

    Field ordering mirrors argument-patterns.md §7.1 minimum required fields.

    For dual-speaker dialogue questions (Type C / Type D variants with two
    speakers), embed two ArgumentGraph instances inside a wrapper — one per
    speaker. The outer container is not defined here; that is a service-layer
    concern.
    """

    model_config = ConfigDict(populate_by_name=True)

    # --- Core structural nodes -------------------------------------------

    premises: list[Node] = Field(
        default_factory=list,
        description=(
            "Explicitly stated supporting claims. Every Node here must have "
            "type=NodeType.premise and implicit=False (or True only if a "
            "premise was inferred rather than quoted — unusual)."
        ),
    )
    assumptions: list[Node] = Field(
        default_factory=list,
        description=(
            "Unstated bridging claims. Nodes here typically have "
            "implicit=True and span=None. These are the 'gap' that a "
            "correct strengthener in UCAT/OC exam questions would fill."
        ),
    )
    conclusion: Node = Field(
        ...,
        description=(
            "The single main claim being argued for (C1). "
            "type must be NodeType.conclusion. "
            "Note: the conclusion is NOT always the last sentence — "
            "'which is why' and 'so that means' can introduce it mid-paragraph."
        ),
    )
    sub_conclusions: list[Node] = Field(
        default_factory=list,
        description=(
            "Intermediate derived claims that act as premises for C1. "
            "Required for depth-3 nested arguments (argument-patterns.md §4.2). "
            "Example: Q20 'there will be far more old people needing care' "
            "is SC1 derived from P1+P2, which then supports C1."
        ),
    )
    counter_premises: list[Node] = Field(
        default_factory=list,
        description=(
            "Claims introduced by 'however / but / yet' that argue against C1. "
            "Required for Type D (counter-premise pivot) arguments. "
            "The counter_premise nodes connect to C1 via edge_type=undermines."
        ),
    )

    # --- Relational structure --------------------------------------------

    edges: list[Edge] = Field(
        default_factory=list,
        description=(
            "All directed edges. Every node ID referenced in an edge "
            "must appear in one of: premises, assumptions, conclusion, "
            "sub_conclusions, counter_premises."
        ),
    )

    # --- Detected errors -------------------------------------------------

    fallacies: list[Fallacy] = Field(
        default_factory=list,
        description=(
            "Detected logical fallacies. Empty list when the argument is "
            "structurally valid (e.g. Type E constraint-satisfaction "
            "arguments never contain fallacies)."
        ),
    )

    # --- Transparency metadata -------------------------------------------

    argument_type: Optional[ArgumentType] = Field(
        default=None,
        description="Structural type from argument-patterns.md §1.1.",
    )
    discourse_markers: list[DiscourseMarker] = Field(
        default_factory=list,
        description=(
            "Connective words detected and their assigned roles. "
            "Used for extraction transparency and debugging."
        ),
    )

    def model_post_init(self, __context: object) -> None:  # noqa: ANN001
        """Cross-field consistency checks — single pass over all nodes."""
        all_nodes: dict[str, NodeType] = {}
        for node in (
            self.premises
            + self.assumptions
            + self.sub_conclusions
            + self.counter_premises
            + [self.conclusion]
        ):
            all_nodes[node.id] = node.type
            if node.implicit and node.span is not None:
                raise ValueError(
                    f"Node {node.id!r} is implicit but has span={node.span!r}."
                )

        for edge in self.edges:
            for src in edge.from_nodes:  # always list[str] after field_validator
                if src not in all_nodes:
                    raise ValueError(
                        f"Edge references unknown source node {src!r}. "
                        "Declare it in premises, assumptions, sub_conclusions, "
                        "counter_premises, or conclusion."
                    )
            if edge.to_node not in all_nodes:
                raise ValueError(
                    f"Edge references unknown target node {edge.to_node!r}."
                )

        for fallacy in self.fallacies:
            for nid in fallacy.node_ids:
                if nid not in all_nodes:
                    raise ValueError(
                        f"Fallacy references unknown node {nid!r}."
                    )


# ---------------------------------------------------------------------------
# Fixture wrapper (used by gold_examples/*.json and tests)
# ---------------------------------------------------------------------------


class AnnotatedArgument(BaseModel):
    """
    Top-level wrapper for gold fixtures and API responses.

    Pairs the raw source text with its extracted ArgumentGraph so that
    character offsets in Node.span can be verified against source_text.
    """

    model_config = ConfigDict(populate_by_name=True)

    source_text: str = Field(
        ...,
        description="The original argument paragraph as it appears in the exam.",
    )
    graph: ArgumentGraph = Field(
        ...,
        description="The extracted argument graph for this source text.",
    )
