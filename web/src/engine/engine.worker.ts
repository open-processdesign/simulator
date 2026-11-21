/// <reference lib="webworker" />
/**
 * Web Worker that runs the OPD engine (Python, via Pyodide) off the main thread.
 * Pyodide and its packages come from the jsDelivr CDN; thermo/chemicals/fluids from PyPI.
 */
import { loadPyodide } from "pyodide";
import { bootEngine, PYODIDE_CDN, type Engine } from "./bootstrap";
import { OPD_ENGINE_SOURCES } from "./sources";
import type { WorkerRequest, WorkerResponse } from "./protocol";
import warmup from "../../../examples/flash-drum.opd.json";

declare const self: DedicatedWorkerGlobalScope;

const post = (message: WorkerResponse) => self.postMessage(message);

// Build-time overrides for self-hosting or offline testing (see web/README.md):
// VITE_PYODIDE_URL — Pyodide distribution base URL; VITE_WHEELS — comma-separated wheel URLs.
const PYODIDE_URL: string = import.meta.env.VITE_PYODIDE_URL || PYODIDE_CDN;
const WHEELS: string[] | undefined = import.meta.env.VITE_WHEELS
  ? (import.meta.env.VITE_WHEELS as string).split(",").map((w) => new URL(w, self.location.href).href)
  : undefined;

const ready: Promise<Engine> = (async () => {
  const start = performance.now();
  post({ type: "progress", step: "load Python runtime" });
  const pyodide = await loadPyodide({ indexURL: new URL(PYODIDE_URL, self.location.href).href });
  const runtimeMs = Math.round(performance.now() - start);
  const engine = await bootEngine(pyodide, {
    sources: OPD_ENGINE_SOURCES,
    wheels: WHEELS,
    warmup,
    onProgress: (step) => post({ type: "progress", step }),
  });
  engine.timings.unshift({ step: "load Python runtime", ms: runtimeMs });
  post({ type: "ready", version: engine.version, timings: engine.timings });
  return engine;
})();

ready.catch((error: unknown) => post({ type: "failed", error: String(error) }));

self.onmessage = async (event: MessageEvent<WorkerRequest>) => {
  const request = event.data;
  const { id, doc } = request;
  try {
    const engine = await ready;
    if (request.type === "validate") {
      post({ id, type: "validate", issues: engine.validate(doc) });
      return;
    }
    if (request.type === "binary_parameters") {
      post({ id, type: "binary_parameters", rows: engine.binaryParameters(doc) });
      return;
    }
    const start = performance.now();
    const result = engine.simulate(doc);
    post({ id, type: "result", result, ms: Math.round(performance.now() - start) });
  } catch (error) {
    post({ id, type: "error", error: String(error) });
  }
};
