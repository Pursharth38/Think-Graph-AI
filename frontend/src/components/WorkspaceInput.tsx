import { useState } from 'react';

interface WorkspaceInputProps {
  onAnalyse: (text: string) => void;
  loading: boolean;
  error: string | null;
  /** Fixture examples the user can load to try the app without typing. */
  examples?: { id: string; preview: string }[];
  onLoadExample?: (id: string) => void;
}

export function WorkspaceInput({
  onAnalyse,
  loading,
  error,
  examples,
  onLoadExample,
}: WorkspaceInputProps) {
  const [text, setText] = useState('');

  const submit = () => {
    const trimmed = text.trim();
    if (trimmed.length === 0 || loading) return;
    onAnalyse(trimmed);
  };

  return (
    <div className="flex h-full flex-col">
      <header className="mb-6">
        <span className="caption-uppercase text-muted">ThinkGraph AI</span>
        <h1 className="display-lg mt-2 text-ink">Map the argument.</h1>
        <p className="font-body mt-3 text-body" style={{ fontSize: 15, maxWidth: 460 }}>
          Paste a UCAT, CLAT or TSA-style argument paragraph. We surface its
          premises, the unstated assumptions it leans on, the conclusion, and
          any logical fallacies.
        </p>
      </header>

      <label htmlFor="argument" className="caption-uppercase mb-2 block text-muted">
        Argument paragraph
      </label>
      <textarea
        id="argument"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submit();
        }}
        placeholder="e.g. It's good for you to have hobbies. They keep you happy and relaxed, so you can study harder…"
        rows={8}
        className="font-body w-full resize-none text-ink outline-none"
        style={{
          background: '#ffffff',
          border: '1px solid #e7e5e4',
          borderRadius: 8,
          padding: 16,
          fontSize: 16,
          lineHeight: 1.5,
        }}
      />

      {error && (
        <p className="font-body mt-3" style={{ color: '#dc2626', fontSize: 14 }}>
          {error}
        </p>
      )}

      <div className="mt-4 flex items-center gap-4">
        <button className="btn-pill" onClick={submit} disabled={loading || text.trim().length === 0}>
          {loading ? 'Analysing…' : 'Analyse argument'}
        </button>
        <span className="font-body text-muted" style={{ fontSize: 13 }}>
          ⌘/Ctrl + Enter
        </span>
      </div>

      {examples && examples.length > 0 && (
        <div className="mt-8">
          <span className="caption-uppercase mb-3 block text-muted">Or try an example</span>
          <ul className="flex flex-col gap-2">
            {examples.map((ex) => (
              <li key={ex.id}>
                <button
                  className="font-body w-full text-left text-body"
                  style={{
                    background: '#fafafa',
                    border: '1px solid #e7e5e4',
                    borderRadius: 12,
                    padding: '10px 14px',
                    fontSize: 14,
                    lineHeight: 1.4,
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    onLoadExample?.(ex.id);
                  }}
                >
                  {ex.preview}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
