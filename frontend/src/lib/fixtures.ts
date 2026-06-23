import { AnnotatedArgument } from '../types/graph';

/** Gold fixtures copied from backend/tests/gold_examples into /public/fixtures. */
export const FIXTURE_IDS = [
  'ex_01',
  'ex_02',
  'ex_03',
  'ex_04',
  'ex_05',
  'ex_06',
  'ex_07',
  'ex_08',
  'ex_09',
  'ex_10',
] as const;

export type FixtureId = (typeof FIXTURE_IDS)[number];

export async function loadFixture(id: FixtureId): Promise<AnnotatedArgument> {
  const res = await fetch(`/fixtures/${id}.json`);
  if (!res.ok) throw new Error(`Could not load fixture ${id}`);
  const data = (await res.json()) as AnnotatedArgument & { _comment?: string };
  return { source_text: data.source_text, graph: data.graph };
}

export function preview(text: string, max = 90): string {
  const clean = text.trim();
  return clean.length > max ? `${clean.slice(0, max)}…` : clean;
}
