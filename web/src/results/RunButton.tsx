import { useTranslation } from "react-i18next";
import { Loader2, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEngine } from "@/engine/EngineProvider";
import { useRun } from "@/state/RunProvider";

/** Primary action: run the flowsheet and open the results. */
export function RunButton({ size = "md" }: { size?: "sm" | "md" }) {
  const { t } = useTranslation();
  const { status } = useEngine();
  const { run, start } = useRun();
  const busy = run.state === "running";
  return (
    <Button
      size={size}
      disabled={status.state !== "ready" || busy}
      onClick={async () => {
        await start();
        window.location.hash = "#/results";
      }}
    >
      {busy ? <Loader2 aria-hidden className="animate-spin" /> : <Play aria-hidden />}
      {busy ? t("run.running") : t("actions.run")}
    </Button>
  );
}
