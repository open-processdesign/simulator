import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { useEngine } from "@/engine/EngineProvider";

/** Small status dot + text in the top bar. Never colour-only: the text says the state. */
export function EngineStatus() {
  const { t } = useTranslation();
  const { status } = useEngine();
  const text =
    status.state === "ready" ? t("engine.ready")
    : status.state === "failed" ? t("engine.failed")
    : status.step ? t("engine.loading_step", { step: status.step })
    : t("engine.loading");
  const title = status.state === "failed" ? t("engine.failed_detail", { error: status.error })
    : status.state === "ready" ? status.version : text;

  return (
    <span role="status" title={title} className="flex max-w-56 items-center gap-1.5 truncate text-xs text-muted">
      <span
        aria-hidden
        className={cn(
          "size-2 shrink-0 rounded-full",
          status.state === "ready" ? "bg-ok" : status.state === "failed" ? "bg-error" : "animate-pulse bg-warn",
        )}
      />
      <span className="truncate">{text}</span>
    </span>
  );
}
