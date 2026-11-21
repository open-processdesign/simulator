import { useTranslation } from "react-i18next";
import { formatNumber } from "@/lib/format";
import type { Flowsheet } from "@/opd/types";
import type { RunResults } from "@/state/RunProvider";
import { showOnCanvas, useSelection } from "@/state/SelectionProvider";
import { cn } from "@/lib/utils";

/**
 * CHEMCAD-style stream table: one column per stream, rows for state and composition.
 * Numbers are monospaced, right-aligned, with units (DESIGN_SYSTEM.md → Numbers).
 */
export function StreamTable({ results, doc, compact = false }: { results: RunResults; doc: Flowsheet; compact?: boolean }) {
  const { t, i18n } = useTranslation();
  const { selection, setSelection } = useSelection();
  const lang = i18n.resolvedLanguage;
  const ids = doc.streams.map((s) => s.id).filter((id) => results.streams[id]);
  const fmt = (v: number | undefined, digits: number) => (v === undefined ? "–" : formatNumber(v, lang, digits));

  const rows: { label: string; unit?: string; cell: (id: string) => string }[] = [
    { label: t("results.from_to"), cell: (id) => { const s = doc.streams.find((x) => x.id === id)!; return `${s.from.unit} → ${s.to.unit}`; } },
    { label: t("flowsheet.specs.temperature"), unit: "K", cell: (id) => fmt(results.streams[id].temperature?.value, 2) },
    { label: t("flowsheet.specs.pressure"), unit: "Pa", cell: (id) => fmt(results.streams[id].pressure?.value, 0) },
    { label: t("flowsheet.specs.molar_flow"), unit: "mol/s", cell: (id) => fmt(results.streams[id].molar_flow?.value, 4) },
    { label: t("flowsheet.specs.vapor_fraction"), unit: "–", cell: (id) => fmt(results.streams[id].vapor_fraction?.value, 4) },
    ...doc.components.map((c) => ({
      label: `x ${c.name}`,
      unit: "–",
      cell: (id: string) => fmt(results.streams[id].mole_fractions?.[c.id], 4),
    })),
  ];

  return (
    <table aria-label={t("results.stream_table")} className={cn("w-full text-sm", compact && "text-xs")}>
      <thead className="sticky top-0 bg-surface-muted text-muted">
        <tr>
          <th scope="col" className="px-3 py-1.5 text-left font-medium">{t("flowsheet.stream")}</th>
          <th scope="col" className="px-2 py-1.5 text-left font-medium">{t("results.unit_col")}</th>
          {ids.map((id) => (
            <th key={id} scope="col" className="num px-3 py-1.5 text-right font-medium">
              <button
                type="button"
                onClick={() => showOnCanvas(setSelection, { kind: "stream", id })}
                className={cn("rounded-sm px-1 hover:text-accent", selection?.kind === "stream" && selection.id === id && "bg-accent-soft text-accent")}
              >
                {id}
              </button>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.label} className="border-t border-border">
            <th scope="row" className="whitespace-nowrap px-3 py-1 text-left font-normal">{r.label}</th>
            <td className="num px-2 py-1 text-muted">{r.unit ?? ""}</td>
            {ids.map((id) => (
              <td key={id} className="num whitespace-nowrap px-3 py-1 text-right">{r.cell(id)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
