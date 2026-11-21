import { useTranslation } from "react-i18next";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { useRun } from "@/state/RunProvider";
import { formatNumber } from "@/lib/format";
import { IssueList } from "./IssueList";
import { RunButton } from "./RunButton";
import { StreamTable } from "./StreamTable";
import { useUnits } from "@/units/UnitSetProvider";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fileName } from "@/state/persistence";
import { downloadText, resultsCsv } from "./csv";
import { ProfileCharts } from "./ProfileChart";

/** Step 5: stream table, unit results and messages of the last run. */
export function ResultsPage() {
  const { t, i18n } = useTranslation();
  const { doc } = useFlowsheet();
  const { run, stale } = useRun();
  const lang = i18n.resolvedLanguage;
  const units = useUnits();

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 px-6 py-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-2xl font-medium">{t("pages.results.title")}</h1>
        <div className="flex items-center gap-2">
          {run.state === "done" && run.results && !stale && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                const tr = lang === "tr";
                const csv = resultsCsv(doc, run.results!, {
                  separator: tr ? ";" : ",",
                  decimal: tr ? "," : ".",
                  label: (k) => t(k),
                  unit: units.unit,
                  toDisplay: units.toDisplay,
                });
                downloadText(csv, fileName(doc).replace(/\.opd\.json$/, "-results.csv"));
              }}
            >
              <Download aria-hidden />
              {t("csv.export")}
            </Button>
          )}
          <RunButton size="sm" />
        </div>
      </div>

      {run.state === "idle" && <p className="text-muted">{t("pages.results.empty")}</p>}
      {run.state === "running" && <p className="text-muted">{t("run.running")}</p>}
      {run.state === "failed" && <p role="alert" className="text-error">{t("results.engine_error", { error: run.error })}</p>}

      {run.state === "done" && (
        <>
          <p role="status" className={run.converged ? "text-sm text-ok" : "text-sm text-error"}>
            {run.converged
              ? t("results.converged", { ms: run.ms, engine: run.results?.engine_version ?? "" })
              : t("results.not_converged")}
          </p>
          {stale && <p className="rounded-md border border-warn bg-surface px-3 py-2 text-sm text-warn">{t("results.stale")}</p>}

          {run.issues.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-base font-semibold">{t("results.messages")}</h2>
              <IssueList issues={run.issues} />
            </section>
          )}

          {run.results && (
            <>
              <section className="flex flex-col gap-2">
                <h2 className="text-base font-semibold">{t("results.stream_table")}</h2>
                <div className="overflow-x-auto rounded-md border border-border bg-surface">
                  <StreamTable results={run.results} doc={doc} />
                </div>
              </section>

              <section className="flex flex-col gap-2">
                <h2 className="text-base font-semibold">{t("results.unit_results")}</h2>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(run.results.units).map(([id, values]) => (
                    <div key={id} className="rounded-md border border-border bg-surface p-3">
                      <h3 className="num mb-1 text-sm font-semibold">{id} <span className="font-sans font-normal text-muted">{t(`units.${doc.units.find((u) => u.id === id)?.type ?? ""}`, { defaultValue: "" })}</span></h3>
                      <dl className="grid grid-cols-[1fr_auto_auto] gap-x-2 text-sm">
                        {Object.entries(values).map(([name, q]) => (
                          <div key={name} className="contents">
                            <dt className="text-muted">
                              {name.startsWith("split_") ? t("flowsheet.split_to", { port: t(`flowsheet.ports.${name.slice(6)}`) })
                                : name.startsWith("extent_") ? t("flowsheet.extent_n", { n: name.slice(7) })
                                : t(`flowsheet.specs.${name}`, { defaultValue: name })}
                            </dt>
                            <dd className="num text-right">{formatNumber(units.toDisplay(name, q.value), lang, units.digits(name))}</dd>
                            <dd className="num text-xs leading-5 text-muted">{units.unit(name)}</dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  ))}
                </div>
              </section>

              {run.results.profiles && Object.keys(run.results.profiles).length > 0 && (
                <section className="flex flex-col gap-3">
                  <h2 className="text-base font-semibold">{t("profiles.heading")}</h2>
                  {Object.entries(run.results.profiles).map(([id, profile]) => (
                    <ProfileCharts key={id} unitId={id} profile={profile} doc={doc} />
                  ))}
                </section>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
