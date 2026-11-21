import type { Flowsheet } from "@/opd/types";
import type { RunResults } from "@/state/RunProvider";

export interface CsvOptions {
  /** Field separator: "," (English) or ";" (Turkish Excel, where "," is the decimal mark). */
  separator: "," | ";";
  decimal: "." | ",";
  /** Translated row labels and headers. */
  label: (key: string) => string;
  /** Display conversion for an OPD quantity name (unit-set aware). */
  unit: (name: string) => string;
  toDisplay: (name: string, si: number) => number;
}

function cell(value: string, sep: string): string {
  return /["\r\n]/.test(value) || value.includes(sep) ? `"${value.replace(/"/g, '""')}"` : value;
}

function num(v: number | undefined, decimal: "." | ","): string {
  if (v === undefined || !Number.isFinite(v)) return "";
  const s = String(Number(v.toPrecision(10)));
  return decimal === "," ? s.replace(".", ",") : s;
}

/**
 * Stream table (one column per stream) followed by unit results (unit, quantity, value, unit).
 * Values are full precision in the chosen unit set; a UTF-8 BOM makes Excel read °C and ü.
 */
export function resultsCsv(doc: Flowsheet, results: RunResults, o: CsvOptions): string {
  const sep = o.separator;
  const line = (cells: string[]) => cells.map((c) => cell(c, sep)).join(sep);
  const ids = doc.streams.map((s) => s.id).filter((id) => results.streams[id]);
  const lines: string[] = [];

  lines.push(line([doc.name]));
  lines.push(line([o.label("results.stream_table")]));
  lines.push(line([o.label("flowsheet.stream"), o.label("results.unit_col"), ...ids]));
  lines.push(line([o.label("results.from_to"), "", ...ids.map((id) => {
    const s = doc.streams.find((x) => x.id === id)!;
    return `${s.from.unit} → ${s.to.unit}`;
  })]));
  for (const field of ["temperature", "pressure", "molar_flow"] as const) {
    lines.push(line([o.label(`flowsheet.specs.${field}`), o.unit(field), ...ids.map((id) => {
      const q = results.streams[id][field];
      return num(q === undefined ? undefined : o.toDisplay(field, q.value), o.decimal);
    })]));
  }
  lines.push(line([o.label("flowsheet.specs.vapor_fraction"), "–", ...ids.map((id) => num(results.streams[id].vapor_fraction?.value, o.decimal))]));
  for (const c of doc.components) {
    lines.push(line([`x ${c.name}`, "–", ...ids.map((id) => num(results.streams[id].mole_fractions?.[c.id], o.decimal))]));
  }

  lines.push("");
  lines.push(line([o.label("results.unit_results")]));
  lines.push(line([o.label("flowsheet.unit"), o.label("csv.quantity"), o.label("csv.value"), o.label("results.unit_col")]));
  for (const [uid, values] of Object.entries(results.units)) {
    for (const [name, q] of Object.entries(values)) {
      lines.push(line([uid, name, num(o.toDisplay(name, q.value), o.decimal), o.unit(name)]));
    }
  }
  return "﻿" + lines.join("\r\n") + "\r\n";
}

export function downloadText(text: string, fileName: string, type = "text/csv;charset=utf-8"): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
