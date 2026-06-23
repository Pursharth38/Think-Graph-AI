import { NodeType } from '../types/graph';

/**
 * Semantic vertical layer (row index, top → bottom) for each node role.
 *
 * Single frontend source of truth, shared by:
 *   - buildReactFlow  — to lay out gold fixtures (which carry no react_flow), and
 *   - GraphCanvas     — to (re)layout any payload for rendering.
 *
 * GraphCanvas derives a node's row from this map and its `nodeType`, NOT from the
 * incoming y coordinate. That keeps rendering independent of whatever spacing the
 * backend graph_builder used, so the two layout implementations can't drift into
 * a broken render. Mirror of backend graph_builder._LAYER_BY_TYPE.
 */
export const LAYER_BY_TYPE: Record<NodeType, number> = {
  premise: 0,
  counter_premise: 0,
  assumption: 1,
  fallacy: 1,
  sub_conclusion: 2,
  conclusion: 3,
};
