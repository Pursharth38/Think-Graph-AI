import { RFNode } from '../types/graph';
import { NODE_META } from '../lib/nodeMeta';
import { socraticFor } from '../lib/socratic';

interface NodeInspectorProps {
  node: RFNode | null;
  onClose: () => void;
}

/** Appears below the canvas on node click — not a modal, not a route. */
export function NodeInspector({ node, onClose }: NodeInspectorProps) {
  if (!node) return null;

  const meta = NODE_META[node.data.nodeType];
  const copy = socraticFor(node.data.nodeType);

  return (
    <section
      className="animate-fade-in-up"
      style={{
        background: '#ffffff',
        borderTop: '1px solid #e7e5e4',
        padding: '24px 28px',
      }}
    >
      <div className="flex items-start justify-between gap-6">
        <div style={{ maxWidth: 760 }}>
          <div className="flex items-center gap-3">
            <span
              className="caption-uppercase"
              style={{
                background: meta.fill,
                color: '#0c0a09',
                borderRadius: 9999,
                padding: '4px 10px',
              }}
            >
              {meta.caption}
            </span>
            <span className="font-body text-muted" style={{ fontSize: 12 }}>
              {node.id}
              {node.data.implicit ? ' · implicit (never stated in text)' : ''}
            </span>
          </div>

          <h3 className="display-sm mt-3 text-ink">{copy.roleTitle}</h3>
          <p className="font-body mt-1" style={{ fontSize: 15, color: '#4e4e4e', lineHeight: 1.5 }}>
            {copy.roleSummary}
          </p>

          <p
            className="font-body mt-4"
            style={{
              fontSize: 16,
              color: '#0c0a09',
              lineHeight: 1.5,
              borderLeft: '2px solid #e7e5e4',
              paddingLeft: 14,
            }}
          >
            “{node.data.label}”
          </p>

          <span className="caption-uppercase mt-5 block text-muted">Ask yourself</span>
          <ul className="mt-2 flex flex-col gap-1.5">
            {copy.questions.map((q, i) => (
              <li key={i} className="font-body" style={{ fontSize: 15, color: '#4e4e4e' }}>
                — {q}
              </li>
            ))}
          </ul>
        </div>

        <button className="btn-text" onClick={onClose} aria-label="Close inspector">
          × Close
        </button>
      </div>
    </section>
  );
}
