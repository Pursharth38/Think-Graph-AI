import { Handle, NodeProps, Position } from 'reactflow';
import { RFNodeData } from '../../types/graph';
import { NODE_META } from '../../lib/nodeMeta';

/**
 * Custom react-flow node, styled per DESIGN.md:
 * white card body, 1px hairline border, 12px radius, a soft pastel role chip
 * keyed off node type. Conclusion renders slightly larger. Fallacy-involved
 * nodes get a peach ring + warning glyph.
 */
export default function ArgumentNode({ data, selected }: NodeProps<RFNodeData>) {
  const meta = NODE_META[data.nodeType];
  const isConclusion = data.nodeType === 'conclusion';
  const hasFallacy = data.hasFallacy === true;

  return (
    <div
      className="font-body text-ink"
      aria-label={`${meta.caption}${data.implicit ? ' (implicit)' : ''}: ${data.label}`}
      style={{
        width: isConclusion ? 250 : 210,
        // Entrance animation lives here (inner card), NOT on the react-flow node
        // wrapper — animating the wrapper's transform would override react-flow's
        // positioning transform and stack all nodes at the origin.
        animation: 'fadeInUp 360ms cubic-bezier(0.16,1,0.3,1) both',
        background: '#ffffff',
        border: hasFallacy
          ? '1.5px solid #f4c5a8'
          : selected
            ? '1.5px solid #0c0a09'
            : '1px solid #e7e5e4',
        borderRadius: 12,
        boxShadow: selected ? '0 4px 16px rgba(0,0,0,0.08)' : '0 1px 2px rgba(0,0,0,0.03)',
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'border-color 140ms ease, box-shadow 140ms ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#d6d3d1', border: 'none' }} />

      {/* Role chip strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 12px',
          background: meta.fill,
        }}
      >
        {hasFallacy && <span aria-hidden>{'⚠'}</span>}
        <span className="caption-uppercase" style={{ color: '#0c0a09' }}>
          {meta.caption}
        </span>
        {data.implicit && (
          <span
            className="caption-uppercase"
            style={{ color: '#0c0a09', opacity: 0.55, letterSpacing: '0.6px' }}
          >
            implicit
          </span>
        )}
      </div>

      <div
        style={{
          padding: '10px 12px 12px',
          fontSize: isConclusion ? 15 : 14,
          lineHeight: 1.45,
          color: '#0c0a09',
        }}
      >
        {data.label}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: '#d6d3d1', border: 'none' }} />
    </div>
  );
}
