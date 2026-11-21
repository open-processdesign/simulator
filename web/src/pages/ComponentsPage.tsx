import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { COMPONENT_SOURCE, componentByCas, searchComponents } from "@/components-db/search";
import { formatNumber } from "@/lib/format";
import { useFlowsheet } from "@/state/FlowsheetProvider";

/** Step 1: choose the chemical components of the process. */
export function ComponentsPage() {
  const { t, i18n } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const [query, setQuery] = useState("");
  const results = useMemo(() => searchComponents(query, 12), [query]);
  const selectedCas = new Set(doc.components.map((c) => c.cas));
  const inputId = useId();
  const lang = i18n.resolvedLanguage;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8">
      <h1 className="font-display text-2xl font-medium">{t("pages.components.title")}</h1>

      <section className="flex flex-col gap-2">
        <label htmlFor={inputId} className="text-sm font-medium">
          {t("components.search_label")}
        </label>
        <div className="flex items-center gap-2 rounded-md border border-border-strong bg-surface px-3 focus-within:shadow-[var(--opd-focus)]">
          <Search aria-hidden className="size-4 text-subtle" />
          <input
            id={inputId}
            type="search"
            autoComplete="off"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("components.search_placeholder")}
            className="h-9 w-full bg-transparent text-sm outline-none placeholder:text-subtle focus-visible:shadow-none [&::-webkit-search-cancel-button]:appearance-none"
          />
        </div>
        {query.trim() && (
          <ul aria-label={t("components.search_label")} className="divide-y divide-border overflow-hidden rounded-md border border-border bg-surface">
            {results.length === 0 && <li className="px-3 py-2 text-sm text-muted">{t("components.no_results", { query })}</li>}
            {results.map((c) => {
              const added = selectedCas.has(c.cas);
              return (
                <li key={c.cas} className="flex items-center gap-3 px-3 py-1.5 text-sm">
                  <span className="flex-1">{c.name}</span>
                  <span className="num w-24 text-muted">{c.formula}</span>
                  <span className="num w-24 text-muted">{c.cas}</span>
                  {added ? (
                    <span className="w-20 text-right text-xs text-muted">{t("components.added")}</span>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-20"
                      aria-label={t("components.add", { name: c.name })}
                      onClick={() => dispatch({ type: "add_component", name: c.name, cas: c.cas, formula: c.formula })}
                    >
                      <Plus aria-hidden />
                      {t("actions.add")}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-base font-semibold">{t("components.selected", { count: doc.components.length })}</h2>
        {doc.components.length === 0 ? (
          <p className="text-sm text-muted">{t("components.none_selected")}</p>
        ) : (
          <table className="w-full overflow-hidden rounded-md border border-border bg-surface text-sm">
            <thead className="bg-surface-muted text-left text-muted">
              <tr>
                <th className="px-3 py-1.5 font-medium">{t("components.name")}</th>
                <th className="px-3 py-1.5 font-medium">{t("components.formula")}</th>
                <th className="px-3 py-1.5 font-medium">{t("components.cas")}</th>
                <th className="px-3 py-1.5 text-right font-medium">{t("components.mw")} [g/mol]</th>
                <th className="px-3 py-1.5 text-right font-medium">{t("components.tb")} [K]</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {doc.components.map((c) => {
                const data = componentByCas(c.cas);
                return (
                  <tr key={c.id} className="border-t border-border">
                    <td className="px-3 py-1.5">{c.name}</td>
                    <td className="num px-3 py-1.5">{c.formula ?? data?.formula ?? "–"}</td>
                    <td className="num px-3 py-1.5">{c.cas}</td>
                    <td className="num px-3 py-1.5 text-right">{data ? formatNumber(data.mw, lang, 2) : "–"}</td>
                    <td className="num px-3 py-1.5 text-right">{data ? formatNumber(data.tb, lang, 2) : "–"}</td>
                    <td className="px-1 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={t("components.remove", { name: c.name })}
                        onClick={() => dispatch({ type: "remove_component", id: c.id })}
                      >
                        <X aria-hidden />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <p className="text-xs text-subtle">{t("components.source", { source: COMPONENT_SOURCE })}</p>
      </section>
    </div>
  );
}
