import { FallacyType, NodeType } from '../types/graph';

/** Visual + label metadata for each logical node role. */
export interface NodeMeta {
  fill: string; // pastel atmospheric token — used softly as node fill
  caption: string; // short uppercase tag
}

export const NODE_META: Record<NodeType, NodeMeta> = {
  premise: { fill: '#a8c8e8', caption: 'Premise' },
  assumption: { fill: '#c8b8e0', caption: 'Assumption' },
  conclusion: { fill: '#a7e5d3', caption: 'Conclusion' },
  sub_conclusion: { fill: '#a7e5d3', caption: 'Sub-conclusion' },
  counter_premise: { fill: '#e8b8c4', caption: 'Counter-premise' },
  fallacy: { fill: '#f4c5a8', caption: 'Fallacy' },
};

export function prettyFallacy(type: FallacyType): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}
