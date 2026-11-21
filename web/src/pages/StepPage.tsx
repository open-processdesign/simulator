import { useTranslation } from "react-i18next";
import { STEPS, type Step } from "@/steps";

/** Empty page for one workflow step; real content comes in later tasks (T05–T07). */
export function StepPage({ step }: { step: Step }) {
  const { t } = useTranslation();
  const current = STEPS.indexOf(step) + 1;

  return (
    <section aria-labelledby={`page-${step}`} className="mx-auto flex max-w-xl flex-col items-center gap-3 px-6 py-24 text-center">
      <p className="num text-xs text-subtle">{t("shell.step_of", { current, total: STEPS.length })}</p>
      <h1 id={`page-${step}`} className="font-display text-2xl font-medium">
        {t(`pages.${step}.title`)}
      </h1>
      <p className="text-muted">{t(`pages.${step}.empty`)}</p>
    </section>
  );
}
