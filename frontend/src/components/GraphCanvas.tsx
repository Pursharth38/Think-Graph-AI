import { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  MarkerType,
  Node,
  Position,
  ReactFlowProvider,
  useNodesInitialized,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { EdgeType, ReactFlowPayload, RFNode } from '../types/graph';
import { LAYER_BY_TYPE } from '../lib/layout';
import ArgumentNode from './graph/ArgumentNode';

const nodeTypes = { argument: ArgumentNode };

// Edge stroke styling keyed off edge type. undermines is rose-toned, the rest
// share the neutral hairline stroke; line style distinguishes semantics.
const EDGE_STYLE: Record<EdgeType, { stroke: string; dash?: string }> = {
  supports: { stroke: '#d6d3d1' },
  enables: { stroke: '#a8c8e8' },
  requires: { stroke: '#c8b8e0', dash: '6 4' },
  undermines: { stroke: '#e8b8c4', dash: '2 4' },
};

/**
 * Layered re-layout that centres each row over the widest row for nicer spacing.
 * Rows come from the node's semantic role (LAYER_BY_TYPE), not the incoming y —
 * so the render is independent of whatever spacing produced the payload.
 */
function layout(rfNodes: RFNode[]): RFNode[] {
  const byLayer = new Map<number, RFNode[]>();
  for (const n of rfNodes) {
    const layer = LAYER_BY_TYPE[n.data.nodeType] ?? 1;
    if (!byLayer.has(layer)) byLayer.set(layer, []);
    byLayer.get(layer)!.push(n);
  }
  const rows = [...byLayer.entries()].sort((a, b) => a[0] - b[0]);
  const X_GAP = 300;
  // Generous row spacing so tall multi-line cards (the conclusion can run several
  // lines) never overlap the row below in flow coordinates.
  const Y_GAP = 240;
  const maxCols = Math.max(...rows.map(([, ns]) => ns.length), 1);
  const totalWidth = (maxCols - 1) * X_GAP;

  const out: RFNode[] = [];
  rows.forEach(([, ns], rowIdx) => {
    const rowWidth = (ns.length - 1) * X_GAP;
    const offset = (totalWidth - rowWidth) / 2;
    ns.forEach((n, col) => {
      out.push({ ...n, position: { x: offset + col * X_GAP, y: rowIdx * Y_GAP } });
    });
  });
  return out;
}

interface GraphCanvasProps {
  payload: ReactFlowPayload | null;
  onNodeClick?: (nodeId: string) => void;
  selectedNodeId?: string | null;
  highlightNodeIds?: string[];
}

function GraphCanvasInner({
  payload,
  onNodeClick,
  selectedNodeId,
  highlightNodeIds,
}: GraphCanvasProps) {
  const { fitView } = useReactFlow();
  // True only once every currently-rendered node has real measured dimensions.
  const nodesInitialized = useNodesInitialized();

  // Build-up animation: reveal nodes row-by-row, then edges.
  const [revealed, setRevealed] = useState(0);
  const [showEdges, setShowEdges] = useState(false);

  const positioned = useMemo(
    () => (payload ? layout(payload.nodes) : []),
    [payload],
  );

  // Order nodes top-to-bottom so premises appear before the conclusion.
  const ordered = useMemo(
    () => [...positioned].sort((a, b) => a.position.y - b.position.y),
    [positioned],
  );

  useEffect(() => {
    if (!payload) return;
    setRevealed(0);
    setShowEdges(false);
    let i = 0;
    const timers: number[] = [];
    const step = () => {
      i += 1;
      setRevealed(i);
      if (i < ordered.length) {
        timers.push(window.setTimeout(step, 150));
      } else {
        timers.push(
          window.setTimeout(() => {
            setShowEdges(true);
            // Guaranteed final fit: by now every node (including the last-revealed
            // one) is in the DOM and measured, so fitView sees the complete graph
            // and zooms to fit it rather than clamping to maxZoom on a partial set.
            timers.push(
              window.setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 260),
            );
          }, 200),
        );
      }
    };
    timers.push(window.setTimeout(step, 120));
    return () => timers.forEach(clearTimeout);
  }, [payload, ordered.length, fitView]);

  // The `fitView` prop only fits once at mount, but nodes appear incrementally via
  // the reveal animation. Re-fit whenever the freshly-revealed nodes have been
  // measured (nodesInitialized) so each fit uses real dimensions instead of
  // over-zooming to a partial/unmeasured set — that earlier bug pinned the
  // viewport at maxZoom and pushed the graph off-canvas.
  useEffect(() => {
    if (!nodesInitialized || revealed === 0) return;
    fitView({ padding: 0.2, duration: 400 });
  }, [nodesInitialized, revealed, showEdges, fitView]);

  const highlight = useMemo(() => new Set(highlightNodeIds ?? []), [highlightNodeIds]);

  const nodes: Node[] = ordered.slice(0, revealed).map((n) => ({
    id: n.id,
    type: 'argument',
    position: n.position,
    sourcePosition: Position.Bottom,
    targetPosition: Position.Top,
    selected: n.id === selectedNodeId,
    data: {
      ...n.data,
      hasFallacy: n.data.hasFallacy || highlight.has(n.id),
    },
    // NOTE: do not put a transform-based animation on the node wrapper — react-flow
    // positions nodes via the wrapper's `transform: translate(x,y)`, and a CSS
    // animation on `transform` overrides it, collapsing every node to the origin.
    // The entrance animation lives on the inner card in ArgumentNode instead.
  }));

  const edges: Edge[] = showEdges
    ? (payload?.edges ?? []).map((e) => {
        const s = EDGE_STYLE[e.type] ?? EDGE_STYLE.supports;
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          type: 'smoothstep',
          animated: e.type === 'undermines',
          markerEnd: { type: MarkerType.ArrowClosed, color: s.stroke, width: 16, height: 16 },
          style: {
            stroke: s.stroke,
            strokeWidth: 1.5,
            strokeDasharray: s.dash,
          },
          labelBgStyle: { fill: '#fafafa' },
          labelStyle: { fill: '#777169', fontSize: 11, fontFamily: 'Inter, sans-serif' },
        } as Edge;
      })
    : [];

  if (!payload) {
    return (
      <div className="flex h-full w-full items-center justify-center text-center">
        <p className="font-body text-body" style={{ maxWidth: 280 }}>
          Paste an argument on the left and press{' '}
          <span style={{ color: '#0c0a09' }}>Analyse</span> to see its logical
          structure here.
        </p>
      </div>
    );
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={(_, node) => onNodeClick?.(node.id)}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.3}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
      style={{ background: '#fafafa' }}
    >
      <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#e7e5e4" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export function GraphCanvas(props: GraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
