import { useTranslation } from "react-i18next";
import { AlertTriangle, CircleX, Info } from "lucide-react";
import type { EngineIssue } from "@/engine/bootstrap";
import { issueText } from "@/flowsheet/SidePanel";
import { showOnCanvas, useSelection, type Selection } from "@/state/SelectionProvider";

/** Issues with a link to the unit or stream they concern (DESIGN_SYSTEM.md → Messages). */
export function IssueList({ issues }: { issues: EngineIssue[] }) {
  const { t } = useTranslation();
  const { setSelection } = useSelection();
  return (
    <ul className="flex flex-col gap-1.5">
      {issues.map((issue, k) => {
        const Icon = issue.severity === "error" ? CircleX : issue.severity === "warning" ? AlertTriangle : Info;
        const color = issue.severity === "error" ? "text-error" : issue.severity === "warning" ? "text-warn" : "text-info";
        const kind = issue.target?.kind;
        const target: Selection = issue.target?.id && (kind === "unit" || kind === "stream") ? { kind, id: issue.target.id } : null;
        return (
          <li key={k} className="flex items-start gap-2 text-sm">
            <Icon aria-label={t(`results.severity.${issue.severity}`)} className={`mt-0.5 size-4 shrink-0 ${color}`} />
            <span className="flex-1">{issueText(t, issue)}</span>
            {target && (
              <button type="button" className="text-xs text-accent hover:underline" onClick={() => showOnCanvas(setSelection, target)}>
                {t("results.show_on_canvas", { id: target.id })}
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
