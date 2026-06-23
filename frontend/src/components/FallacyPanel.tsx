import { Fallacy } from '../types/graph';
import { prettyFallacy } from '../lib/nodeMeta';

interface FallacyPanelProps {
  fallacies: Fallacy[];
  onHighlight: (nodeIds: string[] | null) => void;
}

/**
 * Slides in from the right when fallacies exist. Hovering a card asks the
 * canvas to highlight the involved nodes (data.hasFallacy is already set, but
 * hover gives a stronger, transient highlight).
 */
export function FallacyPanel({ fallacies, onHighlight }: FallacyPanelProps) {
  if (fallacies.length === 0) return null;

  return (
    <aside
      className="animate-slide-in-right flex h-full flex-col"
      style={{
        width: 320,
        background: '#ffffff',
        borderLeft: '1px solid #e7e5e4',
        padding: 24,
        overflowY: 'auto',
      }}
    >
      <div className="mb-5">
        <span className="caption-uppercase text-muted">Detected</span>
        <h2 className="display-sm mt-1 text-ink">
          {fallacies.length} {fallacies.length === 1 ? 'fallacy' : 'fallacies'}
        </h2>
      </div>

      <ul className="flex flex-col gap-4">
        {fallacies.map((f, i) => (
          <li
            key={i}
            onMouseEnter={() => onHighlight(f.node_ids)}
            onMouseLeave={() => onHighlight(null)}
            style={{
              border: '1px solid #e7e5e4',
              borderRadius: 16,
              padding: 16,
              background: '#fafafa',
              cursor: 'default',
            }}
          >
            <span
              className="caption-uppercase"
              style={{
                display: 'inline-block',
                background: '#f4c5a8',
                color: '#0c0a09',
                borderRadius: 9999,
                padding: '4px 10px',
              }}
            >
              {prettyFallacy(f.fallacy_type)}
            </span>

            <p
              className="font-body mt-3"
              style={{ fontSize: 15, lineHeight: 1.5, color: '#4e4e4e' }}
            >
              {f.explanation}
            </p>

            <div className="mt-3 flex items-center justify-between">
              <span className="font-body" style={{ fontSize: 12, color: '#777169' }}>
                Involves {f.node_ids.join(', ')}
              </span>
              <span className="font-body" style={{ fontSize: 12, color: '#777169' }}>
                {Math.round(f.confidence * 100)}% confidence
              </span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
