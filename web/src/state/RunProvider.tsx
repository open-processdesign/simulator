import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { EngineIssue } from "@/engine/bootstrap";
import { useEngine } from "@/engine/EngineProvider";
import type { Flowsheet, StreamState, Quantity } from "@/opd/types";
import { useFlowsheet } from "./FlowsheetProvider";

export interface RunResults {
  engine: string;
  engine_version: string;
  converged: boolean;
  timestamp?: string;
  streams: Record<string, StreamState>;
  units: Record<string, Record<string, Quantity>>;
}

export type RunState =
  | { state: "idle" }
  | { state: "running" }
  | { state: "done"; converged: boolean; results: RunResults | null; issues: EngineIssue[]; ms: number; input: string }
  | { state: "failed"; error: string };

/** What a run depends on: the process data, not the canvas layout or old results. */
export function runInput(doc: Flowsheet): string {
  const { results: _r, layout: _l, ...rest } = doc;
  return JSON.stringify(rest);
}

interface RunContextValue {
  run: RunState;
  /** True when the document changed since the last run. */
  stale: boolean;
  start: () => Promise<void>;
}

const RunContext = createContext<RunContextValue | null>(null);

/** Runs the flowsheet in the engine and keeps the last result (DECISIONS.md D017). */
export function RunProvider({ children }: { children: ReactNode }) {
  const { doc } = useFlowsheet();
  const { client, status } = useEngine();
  const [run, setRun] = useState<RunState>({ state: "idle" });

  const start = useCallback(async () => {
    if (!client || status.state !== "ready") return;
    const input = runInput(doc);
    setRun({ state: "running" });
    try {
      const { result, ms } = await client.simulate(doc);
      const results = result.converged ? (result.document.results as RunResults) : null;
      setRun({ state: "done", converged: result.converged, results, issues: result.issues, ms, input });
    } catch (error) {
      setRun({ state: "failed", error: String(error) });
    }
  }, [client, status.state, doc]);

  const currentInput = useMemo(() => runInput(doc), [doc]);
  const stale = run.state === "done" && run.input !== currentInput;

  return <RunContext.Provider value={{ run, stale, start }}>{children}</RunContext.Provider>;
}

export function useRun() {
  const value = useContext(RunContext);
  if (!value) throw new Error("useRun must be used inside <RunProvider>");
  return value;
}
