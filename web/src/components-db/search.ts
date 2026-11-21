import data from "@/data/components.json";

/** One entry of the component index (built by engine/scripts/build_component_index.py). */
export interface ComponentEntry {
  cas: string;
  name: string;
  formula: string;
  mw: number; // g/mol
  tb: number; // K, normal boiling point
  synonyms: string[];
}

export const COMPONENTS: ComponentEntry[] = (data as { components: ComponentEntry[] }).components;
export const COMPONENT_SOURCE: string = (data as { source: string }).source;

const fold = (s: string) => s.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const INDEX = COMPONENTS.map((entry) => ({
  entry,
  names: [entry.name, ...entry.synonyms].map(fold),
  formula: entry.formula.toLowerCase(),
}));

/**
 * Search by name, synonym, CAS number or formula. Ranking: exact match, then
 * prefix, then word prefix, then substring; ties by shorter name.
 */
export function searchComponents(query: string, limit = 20): ComponentEntry[] {
  const q = fold(query.trim());
  if (!q) return [];
  const scored: { entry: ComponentEntry; score: number }[] = [];
  for (const { entry, names, formula } of INDEX) {
    let score = 0;
    if (entry.cas === q || formula === q) score = 100;
    for (const name of names) {
      if (name === q) score = Math.max(score, 90);
      else if (name.startsWith(q)) score = Math.max(score, 70);
      else if (name.split(/[\s,-]+/).some((w) => w.startsWith(q))) score = Math.max(score, 50);
      else if (name.includes(q)) score = Math.max(score, 30);
    }
    if (!score && entry.cas.startsWith(q)) score = 40;
    if (score) scored.push({ entry, score });
  }
  scored.sort((a, b) => b.score - a.score || a.entry.name.length - b.entry.name.length || a.entry.name.localeCompare(b.entry.name));
  return scored.slice(0, limit).map((s) => s.entry);
}

export function componentByCas(cas: string): ComponentEntry | undefined {
  return COMPONENTS.find((c) => c.cas === cas);
}
