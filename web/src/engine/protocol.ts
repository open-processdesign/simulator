import type { BinaryParameterRow, EngineResult, Timing } from "./bootstrap";

/** Messages from the page to the engine worker. */
export type WorkerRequest =
  | { id: number; type: "simulate"; doc: unknown }
  | { id: number; type: "binary_parameters"; doc: unknown };

/** Messages from the engine worker to the page. */
export type WorkerResponse =
  | { type: "progress"; step: string }
  | { type: "ready"; version: string; timings: Timing[] }
  | { type: "failed"; error: string }
  | { id: number; type: "result"; result: EngineResult; ms: number }
  | { id: number; type: "binary_parameters"; rows: BinaryParameterRow[] }
  | { id: number; type: "error"; error: string };
