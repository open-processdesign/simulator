import { useTranslation } from "react-i18next";
import { LANGUAGES, rememberLanguage, type Language } from "@/i18n";
import { WorkflowNav } from "@/components/WorkflowNav";
import { EngineStatus } from "@/components/EngineStatus";
import { RunButton } from "@/results/RunButton";
import type { Step } from "@/steps";

interface TopBarProps {
  step: Step;
  onStepChange: (step: Step) => void;
}

/** Top bar (48 px): logo · app name · workflow steps · language. */
export function TopBar({ step, onStepChange }: TopBarProps) {
  const { t, i18n } = useTranslation();

  return (
    <header className="flex h-topbar shrink-0 items-center gap-6 border-b border-border bg-surface px-4">
      <div className="flex items-center gap-2">
        <img src="./favicon.svg" alt="" className="size-5" />
        <span className="text-base font-semibold">{t("app.name")}</span>
      </div>

      <WorkflowNav current={step} onChange={onStepChange} />

      <div className="ml-auto flex items-center gap-4">
        <EngineStatus />
        <RunButton size="sm" />
      </div>

      <label className="flex items-center gap-2 text-sm text-muted">
        <span>{t("shell.language")}</span>
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
