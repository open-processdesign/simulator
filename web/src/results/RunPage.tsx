import { useTranslation } from "react-i18next";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { useEngine } from "@/engine/EngineProvider";
import { useIssues } from "@/flowsheet/useIssues";
import { IssueList } from "./IssueList";
import { RunButton } from "./RunButton";

/** Step 4: check what is missing, then run. */
export function RunPage() {
  const { t } = useTranslation();
  const { doc } = useFlowsheet();
  const { status } = useEngine();
  const issues = useIssues(doc, 0);
  const errors = issues?.filter((i) => i.severity === "error") ?? [];

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 px-6 py-8">
      <h1 className="font-display text-2xl font-medium">{t("pages.run.title")}</h1>
      <dl className="grid grid-cols-3 gap-3 text-sm">
        {[
          [t("run.components"), doc.components.length],
          [t("run.units"), doc.units.length],
          [t("run.streams"), doc.streams.length],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md border border-border bg-surface p-3">
            <dt className="text-muted">{k}</dt>
            <dd className="num text-xl">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="text-sm text-muted">{t("run.package", { name: t(`thermo.packages.${doc.thermo.package}.name`) })}</p>

      {status.state !== "ready" ? (
        <p className="text-sm text-muted">{t("thermo.binary_waiting")}</p>
      ) : issues === null ? null : errors.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-base font-semibold">{t("run.fix_first", { count: errors.length })}</h2>
          <IssueList issues={errors} />
        </section>
      ) : (
        <p className="text-sm text-ok">{t("run.ready")}</p>
      )}

      <div>
        <RunButton />
      </div>
    </div>
  );
}
