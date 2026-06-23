"""
graph_builder: ArgumentGraph -> react-flow {nodes, edges} payload.

The frontend (graph-frontend agent) renders the argument as an interactive DAG with
react-flow. react-flow expects:

  nodes: [ { "id", "type", "data": {...}, "position": {"x", "y"} } ]
  edges: [ { "id", "source", "target", "type", "label", "data": {...} } ]

This module is pure / deterministic (no LLM). It assigns a simple layered layout so the
frontend has sensible default positions; the frontend may re-layout with dagre/elk.

Layering (top -> bottom): premises & counter_premises -> assumptions -> sub_conclusions
-> conclusion. This mirrors the typical support flow.
"""

from __future__ import annotations

from app.models.graph import ArgumentGraph, Node, NodeType

# Visual layout constants (frontend can override)
_X_SPACING = 220
_Y_SPACING = 140

# Which layer (row) each node type sits in.
_LAYER_BY_TYPE: dict[NodeType, int] = {
    NodeType.premise: 0,
    NodeType.counter_premise: 0,
    NodeType.assumption: 1,
    NodeType.sub_conclusion: 2,
    NodeType.conclusion: 3,
    NodeType.fallacy: 1,
}


def _node_to_rf(node: Node, x: int, y: int) -> dict:
    return {
        "id": node.id,
        "type": node.type.value,  # frontend keys its custom node components off this
        "position": {"x": x, "y": y},
        "data": {
            "label": node.text,
            "nodeType": node.type.value,
            "implicit": node.implicit,
            "span": list(node.span) if node.span is not None else None,
        },
    }


def build_react_flow(graph: ArgumentGraph) -> dict:
    """Convert an ArgumentGraph into a react-flow {nodes, edges} dict."""
    layered: dict[int, list[Node]] = {}

    all_nodes: list[Node] = (
        list(graph.premises)
        + list(graph.counter_premises)
        + list(graph.assumptions)
        + list(graph.sub_conclusions)
        + [graph.conclusion]
    )
    for node in all_nodes:
        layer = _LAYER_BY_TYPE.get(node.type, 1)
        layered.setdefault(layer, []).append(node)

    rf_nodes: list[dict] = []
    for layer, nodes in sorted(layered.items()):
        for col, node in enumerate(nodes):
            x = col * _X_SPACING
            y = layer * _Y_SPACING
            rf_nodes.append(_node_to_rf(node, x, y))

    # Collect fallacy involvement so the frontend can flag affected nodes.
    fallacy_nodes: set[str] = set()
    for fallacy in graph.fallacies:
        fallacy_nodes.update(fallacy.node_ids)
    if fallacy_nodes:
        for rf_node in rf_nodes:
            if rf_node["id"] in fallacy_nodes:
                rf_node["data"]["hasFallacy"] = True

    rf_edges: list[dict] = []
    for i, edge in enumerate(graph.edges):
        for src in edge.from_nodes:
            rf_edges.append(
                {
                    "id": f"e{i}-{src}-{edge.to_node}",
                    "source": src,
                    "target": edge.to_node,
                    "type": edge.edge_type.value,
                    "label": edge.edge_type.value,
                    "data": {"edgeType": edge.edge_type.value},
                }
            )

    return {
        "nodes": rf_nodes,
        "edges": rf_edges,
        "argument_type": graph.argument_type.value if graph.argument_type else None,
        "fallacies": [f.model_dump() for f in graph.fallacies],
    }
