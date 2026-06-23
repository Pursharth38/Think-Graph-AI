import { useEffect, useMemo, useState } from 'react';
import { WorkspaceInput } from './components/WorkspaceInput';
import { GraphCanvas } from './components/GraphCanvas';
import { FallacyPanel } from './components/FallacyPanel';
import { NodeInspector } from './components/NodeInspector';
import { useExtraction } from './hooks/useExtraction';
import { FIXTURE_IDS, FixtureId, loadFixture, preview } from './lib/fixtures';
import { RFNode } from './types/graph';

export default function App() {
  const { result, loading, error, analyse, loadFixture: showFixture } = useExtraction();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [highlightIds, setHighlightIds] = useState<string[] | null>(null);
  const [examples, setExamples] = useState<{ id: string; preview: string }[]>([]);

  // Pull a few fixture previews so the user can try the app offline.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const picks: FixtureId[] = [FIXTURE_IDS[0], FIXTURE_IDS[2], FIXTURE_IDS[6]];
      const loaded = await Promise.all(
        picks.map(async (id) => {
          try {
            const f = await loadFixture(id);
            return { id: id as string, preview: preview(f.source_text) };
          } catch {
            return null;
          }
        }),
      );
      if (!cancelled) setExamples(loaded.filter((x): x is { id: string; preview: string } => x !== null));
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onLoadExample = async (id: string) => {
    try {
      const f = await loadFixture(id as FixtureId);
      setSelectedNodeId(null);
      setHighlightIds(null);
      showFixture(f);
    } catch {
      /* ignore — fixture missing */
    }
  };

  const rf = result?.react_flow ?? null;
  const fallacies = rf?.fallacies ?? [];

  const selectedNode: RFNode | null = useMemo(() => {
    if (!rf || !selectedNodeId) return null;
    return rf.nodes.find((n) => n.id === selectedNodeId) ?? null;
  }, [rf, selectedNodeId]);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-canvas lg:flex-row">
      {/* Left — workspace input (40%) */}
      <div
        className="overflow-y-auto"
        style={{ flexBasis: '40%', maxWidth: 560, padding: '40px 40px 32px' }}
      >
        <WorkspaceInput
          onAnalyse={(text) => {
            setSelectedNodeId(null);
            setHighlightIds(null);
            analyse(text);
          }}
          loading={loading}
          error={error}
          examples={examples}
          onLoadExample={onLoadExample}
        />
      </div>

      {/* Right — graph + panels (60%) */}
      <div className="relative flex min-w-0 flex-1 flex-col">
        {/* Atmospheric gradient orb — decoration only, behind the canvas */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            top: -120,
            right: -80,
            width: 380,
            height: 380,
            borderRadius: '9999px',
            background:
              'radial-gradient(circle at 30% 30%, #a7e5d3 0%, rgba(167,229,211,0) 70%)',
            filter: 'blur(8px)',
            pointerEvents: 'none',
            zIndex: 0,
          }}
        />

        {result?.degraded && (
          <div
            className="font-body"
            style={{
              position: 'relative',
              zIndex: 1,
              margin: 16,
              padding: '12px 16px',
              background: '#fafafa',
              border: '1px solid #e7e5e4',
              borderRadius: 12,
              color: '#777169',
              fontSize: 14,
            }}
          >
            Showing a simplified graph. The full analysis was unavailable this time, so
            fallacy detection and some assumptions may be missing.
          </div>
        )}

        <div className="relative z-[1] flex min-h-0 flex-1">
          <div className="min-w-0 flex-1">
            <GraphCanvas
              payload={rf}
              selectedNodeId={selectedNodeId}
              highlightNodeIds={highlightIds ?? undefined}
              onNodeClick={(id) => setSelectedNodeId((cur) => (cur === id ? null : id))}
            />
          </div>

          <FallacyPanel fallacies={fallacies} onHighlight={setHighlightIds} />
        </div>

        <NodeInspector node={selectedNode} onClose={() => setSelectedNodeId(null)} />
      </div>
    </div>
  );
}
