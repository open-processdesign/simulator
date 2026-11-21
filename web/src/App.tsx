import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { TopBar } from "@/components/TopBar";
import { StepPage } from "@/pages/StepPage";
import { stepFromHash, type Step } from "@/steps";

export function App() {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>(() => stepFromHash(window.location.hash));

  useEffect(() => {
    const onHashChange = () => setStep(stepFromHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <div className="flex h-full flex-col">
      <TopBar step={step} onStepChange={setStep} />
      <main className="flex-1 overflow-auto">
        <StepPage step={step} />
      </main>
      <footer className="border-t border-border bg-surface-muted px-4 py-1.5 text-xs text-muted">
        {t("app.disclaimer")}
      </footer>
    </div>
  );
}
