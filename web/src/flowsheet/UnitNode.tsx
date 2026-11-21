import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { unitDef } from "./catalog";
import { CATEGORY_COLOR, UNIT_ICONS } from "./icons";
import type { UnitStatus } from "./useIssues";

export type NodeStatus = UnitStatus | "solved";
export type UnitNodeData = { unitType: string; label?: string; status: NodeStatus };
export type UnitNodeType = Node<UnitNodeData, "unit">;

const STATUS_DOT: Record<NodeStatus, string> = {
  solved: "bg-ok",
  ok: "bg-surface ring-1 ring-ok",
  missing: "bg-warn",
  error: "bg-error",
  unknown: "bg-border-strong",
};

/** Spread handles evenly along one side. */
const offset = (index: number, count: number) => `${((index + 1) / (count + 1)) * 100}%`;

function UnitNodeView({ id, data, selected }: NodeProps<UnitNodeType>) {
  const { t } = useTranslation();
  const def = unitDef(data.unitType);
  const Icon = UNIT_ICONS[data.unitType];
  const inlets = def?.inlets ?? [];
  const outlets = def?.outlets ?? [];
  const statusText = t(`flowsheet.status.${data.status}`);

  return (
    <div
      className={cn(
        "relative flex min-h-16 w-28 flex-col items-center justify-center gap-1 rounded-md border bg-surface px-2 py-2 text-center",
        selected ? "border-accent shadow-[var(--opd-focus)]" : "border-border-strong",
      )}
    >
      <span
        role="img"
        aria-label={statusText}
        title={statusText}
        className={cn("absolute right-1.5 top-1.5 size-2 rounded-full", STATUS_DOT[data.status])}
      />
      {Icon && <Icon aria-hidden className="size-5" style={{ color: def ? CATEGORY_COLOR[def.category] : undefined }} />}
      <span className="num text-xs font-medium leading-tight">{id}</span>
      {data.label && <span className="text-[11px] leading-tight text-muted">{data.label}</span>}

      {inlets.map((port, i) => (
        <Handle
          key={port}
          id={port}
          type="target"
          position={Position.Left}
          style={{ top: offset(i, inlets.length) }}
          className="!size-2.5 !border-border-strong !bg-surface"
          title={t(`flowsheet.ports.${port}`)}
        />
      ))}
      {outlets.map((port, i) => (
        <Handle
          key={port}
          id={port}
          type="source"
          position={Position.Right}
          style={{ top: offset(i, outlets.length) }}
          className="!size-2.5 !border-border-strong !bg-surface-muted"
          title={t(`flowsheet.ports.${port}`)}
        />
      ))}
    </div>
  );
}

export const UnitNode = memo(UnitNodeView);
