import { useCallback, useRef, useState } from 'react';
import { ExtractResponse } from '../types/graph';
import { buildReactFlow } from '../lib/buildReactFlow';
import { AnnotatedArgument } from '../types/graph';

const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');

interface ExtractionState {
  result: ExtractResponse | null;
  loading: boolean;
  error: string | null;
}

const INITIAL: ExtractionState = { result: null, loading: false, error: null };

export function useExtraction() {
  const [state, setState] = useState<ExtractionState>(INITIAL);
  // Monotonic id of the most recently *initiated* action (live analyse OR fixture
  // load). A live call can take tens of seconds; if the user picks a fixture or
  // re-analyses while it is in flight, the stale response must NOT clobber the
  // newer result. Each action claims an id and only commits if it is still latest.
  const latestRequest = useRef(0);
  const inFlight = useRef<AbortController | null>(null);

  /** Live call to POST /extract. */
  const analyse = useCallback(async (sourceText: string) => {
    const requestId = (latestRequest.current += 1);
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;

    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_text: sourceText, include_react_flow: true }),
        signal: controller.signal,
      });
      if (!res.ok) {
        throw new Error(`Backend returned ${res.status} ${res.statusText}`);
      }
      const data = (await res.json()) as ExtractResponse;
      // Defensive: if backend omitted react_flow, derive it client-side.
      if (!data.react_flow && data.graph) {
        data.react_flow = buildReactFlow(data.graph);
      }
      if (requestId !== latestRequest.current) return; // superseded — drop it
      setState({ result: data, loading: false, error: null });
    } catch (err) {
      // Aborted because a newer action started: stay silent, the newer one owns state.
      if (err instanceof DOMException && err.name === 'AbortError') return;
      if (requestId !== latestRequest.current) return;
      const message =
        err instanceof Error ? err.message : 'Something went wrong analysing the argument.';
      setState({
        result: null,
        loading: false,
        error: `Could not reach the analysis service. ${message}. Is the backend running on ${API_URL}? You can still explore the example arguments.`,
      });
    }
  }, []);

  /** Load a gold fixture (AnnotatedArgument) without hitting the backend. */
  const loadFixture = useCallback((annotated: AnnotatedArgument) => {
    // Claim latest + cancel any in-flight live call so its late response can't win.
    latestRequest.current += 1;
    inFlight.current?.abort();
    inFlight.current = null;
    const response: ExtractResponse = {
      source_text: annotated.source_text,
      graph: annotated.graph,
      react_flow: buildReactFlow(annotated.graph),
      degraded: false,
    };
    setState({ result: response, loading: false, error: null });
  }, []);

  const reset = useCallback(() => {
    latestRequest.current += 1;
    inFlight.current?.abort();
    inFlight.current = null;
    setState(INITIAL);
  }, []);

  return { ...state, analyse, loadFixture, reset };
}
