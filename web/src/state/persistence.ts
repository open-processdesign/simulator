import type { Flowsheet } from "@/opd/types";

const DRAFT_KEY = "opd.draft";

/** Last edited document, kept in this browser only (light convenience; may be unavailable). */
export function loadDraft(): Flowsheet | null {
  try {
    const text = window.localStorage.getItem(DRAFT_KEY);
    if (!text) return null;
    const parsed = parseDocument(text);
    return parsed.ok ? parsed.doc : null;
  } catch {
    return null;
  }
}

export function saveDraft(doc: Flowsheet): void {
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(doc));
  } catch {
    // Storage full or blocked: the draft simply is not kept.
  }
}

export type ParseResult = { ok: true; doc: Flowsheet } | { ok: false; reason: "json" | "format" };

/** Accept an OPD flowsheet file; the engine checks the details when it validates or runs. */
export function parseDocument(text: string): ParseResult {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return { ok: false, reason: "json" };
  }
  const d = data as Partial<Flowsheet>;
  if (!d || d.format !== "opd-flowsheet" || d.version !== "0.1" || !Array.isArray(d.components)
      || !Array.isArray(d.units) || !Array.isArray(d.streams) || !d.thermo) {
    return { ok: false, reason: "format" };
  }
  return { ok: true, doc: d as Flowsheet };
}

/** File name from the process name: "Benzene column" → "benzene-column.opd.json". */
export function fileName(doc: Flowsheet): string {
  const base = doc.name.replace(/ı/g, "i").replace(/İ/g, "I").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "flowsheet";
  return `${base}.opd.json`;
}

/** Save as a file the user can keep, share and open again (results are not saved). */
export function downloadDocument(doc: Flowsheet): void {
  const { results: _results, ...rest } = doc;
  const blob = new Blob([JSON.stringify(rest, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName(doc);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
