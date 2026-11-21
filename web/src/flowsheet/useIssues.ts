import { useEffect, useState } from "react";
import type { EngineIssue } from "@/engine/bootstrap";
import { useEngine } from "@/engine/EngineProvider";
import type { Flowsheet } from "@/opd/types";

/** Engine input checks for the current document, refreshed shortly after each edit. */
export function useIssues(doc: Flowsheet, delayMs = 250): EngineIssue[] | null {
  const { status, client } = useEngine();
  const [issues, setIssues] = useState<EngineIssue[] | null>(null);

  useEffect(() => {
    if (status.state !== "ready" || !client) return;
    let alive = true;
    const timer = setTimeout(() => {
      client.validate(doc).then((r) => alive && setIssues(r)).catch(() => alive && setIssues(null));
    }, delayMs);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [client, status.state, doc, delayMs]);

  return issues;
}

export type UnitStatus = "ok" | "missing" | "error" | "unknown";

const MISSING = new Set(["missing_spec", "unconnected_port", "too_few_outlets", "split_needs_one_open_outlet"]);

/** Issues that belong to a unit: its own, plus those on a feed's outgoing stream. */
export function issuesForUnit(unitId: string, doc: Flowsheet, issues: EngineIssue[]): EngineIssue[] {
  const unit = doc.units.find((u) => u.id === unitId);
  const feedStreams = unit?.type === "feed" ? doc.streams.filter((s) => s.from.unit === unitId).map((s) => s.id) : [];
  return issues.filter(
    (i) => (i.target?.kind === "unit" && i.target.id === unitId) || (i.target?.kind === "stream" && feedStreams.includes(i.target.id ?? "")),
  );
}

export function unitStatus(unitId: string, doc: Flowsheet, issues: EngineIssue[] | null): UnitStatus {
  if (!issues) return "unknown";
  const own = issuesForUnit(unitId, doc, issues).filter((i) => i.severity === "error");
  if (own.length === 0) return "ok";
  return own.every((i) => MISSING.has(i.code)) ? "missing" : "error";
}
