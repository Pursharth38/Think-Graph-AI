/**
 * Client-side mirror of backend/app/services/graph_builder.build_react_flow.
 *
 * The live /extract endpoint returns a ready-made `react_flow` payload, so the
 * UI never needs this at runtime against the backend. But the gold fixtures
 * (AnnotatedArgument) only carry `graph`, so we reproduce the same layered
 * layout here to develop against fixtures with an identical payload shape.
 */
import {
  ArgumentGraph,
  GraphNode,
  NodeType,
  ReactFlowPayload,
  RFEdge,
  RFNode,
  edgeSources,
} from '../types/graph';

const X_SPACING = 220;
const Y_SPACING = 140;

const LAYER_BY_TYPE: Record<NodeType, number> = {
  premise: 0,
  counter_premise: 0,
  assumption: 1,
  fallacy: 1,
  sub_conclusion: 2,
  conclusion: 3,
};

function toRF(node: GraphNode, x: number, y: number): RFNode {
  return {
    id: node.id,
    type: node.type,
    position: { x, y },
    data: {
      label: node.text,
      nodeType: node.type,
      implicit: node.implicit,
      span: node.span,
    },
  };
}

export function buildReactFlow(graph: ArgumentGraph): ReactFlowPayload {
  const allNodes: GraphNode[] = [
    ...graph.premises,
    ...graph.counter_premises,
    ...graph.assumptions,
    ...graph.sub_conclusions,
    graph.conclusion,
  ];

  const layered = new Map<number, GraphNode[]>();
  for (const node of allNodes) {
    const layer = LAYER_BY_TYPE[node.type] ?? 1;
    if (!layered.has(layer)) layered.set(layer, []);
    layered.get(layer)!.push(node);
  }

  const rfNodes: RFNode[] = [];
  for (const layer of [...layered.keys()].sort((a, b) => a - b)) {
    layered.get(layer)!.forEach((node, col) => {
      rfNodes.push(toRF(node, col * X_SPACING, layer * Y_SPACING));
    });
  }

  const fallacyNodes = new Set<string>();
  for (const f of graph.fallacies) f.node_ids.forEach((id) => fallacyNodes.add(id));
  for (const n of rfNodes) {
    if (fallacyNodes.has(n.id)) n.data.hasFallacy = true;
  }

  const rfEdges: RFEdge[] = [];
  graph.edges.forEach((edge, i) => {
    for (const src of edgeSources(edge)) {
      rfEdges.push({
        id: `e${i}-${src}-${edge.to_node}`,
        source: src,
        target: edge.to_node,
        type: edge.edge_type,
        label: edge.edge_type,
        data: { edgeType: edge.edge_type },
      });
    }
  });

  return {
    nodes: rfNodes,
    edges: rfEdges,
    argument_type: graph.argument_type,
    fallacies: graph.fallacies,
  };
}
