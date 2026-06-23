/**
 * TypeScript mirror of the backend Pydantic contract.
 *
 * Sources of truth:
 *   - backend/app/models/graph.py        (ArgumentGraph / Node / Edge / Fallacy)
 *   - backend/app/services/graph_builder.py (react_flow payload shape)
 *   - backend/app/routers/extraction.py   (POST /extract request + response)
 *
 * NOTE: edges in `graph` use the JSON alias "from" (not "from_nodes").
 */

export type NodeType =
  | 'premise'
  | 'assumption'
  | 'conclusion'
  | 'sub_conclusion'
  | 'counter_premise'
  | 'fallacy';

export type EdgeType = 'supports' | 'undermines' | 'enables' | 'requires';

export type FallacyType =
  | 'affirming_the_consequent'
  | 'denying_the_antecedent'
  | 'hasty_generalization'
  | 'equivocation'
  | 'false_dichotomy'
  | 'slippery_slope'
  | 'circular_reasoning'
  | 'straw_man'
  | 'ad_hominem'
  | 'tu_quoque';

export type ArgumentType =
  | 'single_premise_implicit_assumption'
  | 'two_premise_causal_gap'
  | 'chain_conditional'
  | 'counter_premise_pivot'
  | 'constraint_satisfaction';

// --- ArgumentGraph (the `graph` field) -------------------------------------

export interface GraphNode {
  id: string;
  text: string;
  type: NodeType;
  span: [number, number] | null;
  implicit: boolean;
}

export interface GraphEdge {
  /** JSON alias of from_nodes. Coerced to an array by the backend validator. */
  from: string[] | string;
  to_node: string;
  edge_type: EdgeType;
}

export interface Fallacy {
  node_ids: string[];
  fallacy_type: FallacyType;
  explanation: string;
  confidence: number;
}

export interface DiscourseMarker {
  marker: string;
  span: [number, number] | null;
  assigned_role: string;
  is_misleading: boolean;
}

export interface ArgumentGraph {
  premises: GraphNode[];
  assumptions: GraphNode[];
  conclusion: GraphNode;
  sub_conclusions: GraphNode[];
  counter_premises: GraphNode[];
  edges: GraphEdge[];
  fallacies: Fallacy[];
  argument_type: ArgumentType | null;
  discourse_markers: DiscourseMarker[];
}

// --- react_flow payload (graph_builder.build_react_flow) -------------------

export interface RFNodeData {
  label: string;
  nodeType: NodeType;
  implicit: boolean;
  span: [number, number] | null;
  hasFallacy?: boolean;
}

export interface RFNode {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  data: RFNodeData;
}

export interface RFEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label: string;
  data: { edgeType: EdgeType };
}

export interface ReactFlowPayload {
  nodes: RFNode[];
  edges: RFEdge[];
  argument_type: ArgumentType | null;
  fallacies: Fallacy[];
}

// --- POST /extract request + response --------------------------------------

export interface ExtractRequest {
  source_text: string;
  include_react_flow: boolean;
}

export interface ExtractResponse {
  source_text: string;
  graph: ArgumentGraph;
  react_flow: ReactFlowPayload | null;
  degraded: boolean;
}

/**
 * Gold-fixture shape (backend/tests/gold_examples/*.json) is an
 * AnnotatedArgument: { source_text, graph }. It has no react_flow.
 */
export interface AnnotatedArgument {
  source_text: string;
  graph: ArgumentGraph;
}

/** Normalise an edge's `from` field to a string[] regardless of source shape. */
export function edgeSources(edge: GraphEdge): string[] {
  return Array.isArray(edge.from) ? edge.from : [edge.from];
}
