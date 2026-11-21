import { useTranslation } from "react-i18next";
import { LANGUAGES, rememberLanguage, type Language } from "@/i18n";
import { WorkflowNav } from "@/components/WorkflowNav";
import { EngineStatus } from "@/components/EngineStatus";
import { RunButton } from "@/results/RunButton";
import { FileMenu, ProcessName } from "@/components/FileMenu";
import { useUnits } from "@/units/UnitSetProvider";
import { UNIT_SETS } from "@/units/units";
import type { Step } from "@/steps";

interface TopBarProps {
  step: Step;
  onStepChange: (step: Step) => void;
}

/** Top bar (48 px): logo · app name · workflow steps · language. */
export function TopBar({ step, onStepChange }: TopBarProps) {
  const { t, i18n } = useTranslation();
  const units = useUnits();

  return (
    <header className="flex h-topbar shrink-0 items-center gap-4 border-b border-border bg-surface px-4">
      <div className="flex items-center gap-2">
        <img src="./favicon.svg" alt="" className="size-5" />
        <span className="whitespace-nowrap text-base font-semibold">{t("app.name")}</span>
        <FileMenu />
        <ProcessName />
      </div>

      <WorkflowNav current={step} onChange={onStepChange} />

      <div className="ml-auto flex items-center gap-4">
        <EngineStatus />
        <RunButton size="sm" />
      </div>

      <label className="flex items-center gap-2 text-sm text-muted">
        <span className="sr-only">{t("shell.units")}</span>
        <select
          title={t(`shell.unit_sets_long.${units.set}`)}
          className="h-7 rounded-sm border border-border-strong bg-surface px-2 text-sm text-text"
          value={units.set}
          onChange={(event) => units.setSet(event.target.value as (typeof UNIT_SETS)[number])}
        >
          {UNIT_SETS.map((u) => (
            <option key={u} value={u}>{t(`shell.unit_sets.${u}`)}</option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-muted">
        <span className="sr-only">{t("shell.language")}</span>
        <select
          className="h-7 rounded-sm border border-border-strong bg-surface px-2 text-sm text-text"
          value={i18n.resolvedLanguage}
          onChange={(event) => {
            const lng = event.target.value as Language;
            rememberLanguage(lng);
            void i18n.changeLanguage(lng);
          }}
        >
          {LANGUAGES.map((lng) => (
            <option key={lng} value={lng}>
              {t(`languages.${lng}`)}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}
