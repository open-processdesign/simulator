import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { STEPS, type Step } from "@/steps";

interface WorkflowNavProps {
  current: Step;
  onChange: (step: Step) => void;
}

/**
 * Components → Thermodynamics → Flowsheet → Run → Results.
 * The current step is the only element in the accent colour.
 * (Completed-step checks arrive once steps can be completed.)
 */
export function WorkflowNav({ current, onChange }: WorkflowNavProps) {
  const { t } = useTranslation();

  return (
    <nav aria-label={t("shell.steps_label")}>
      <ol className="flex items-center gap-1">
        {STEPS.map((step, index) => {
          const active = step === current;
          return (
            <li key={step} className="flex items-center gap-1">
              {index > 0 && (
                <span aria-hidden className="text-subtle">
                  ›
                </span>
              )}
              <a
                href={`#/${step}`}
                aria-current={active ? "step" : undefined}
                onClick={() => onChange(step)}
                className={cn(
                  "flex items-center gap-1.5 rounded-sm px-2 py-1 text-sm no-underline transition-colors",
                  active
                    ? "bg-accent-soft font-medium text-accent"
                    : "text-muted hover:bg-surface-muted hover:text-text",
                )}
              >
                <span className="num text-xs">{index + 1}</span>
                {t(`steps.${step}`)}
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
