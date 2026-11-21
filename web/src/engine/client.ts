import type { BinaryParameterRow, EngineResult, Timing } from "./bootstrap";
import type { WorkerRequest, WorkerResponse } from "./protocol";

export interface EngineInfo {
  version: string;
  timings: Timing[];
}

export interface EngineClient {
  /** Resolves once Python, the packages and the engine are loaded. */
  ready: Promise<EngineInfo>;
  simulate(doc: unknown): Promise<{ result: EngineResult; ms: number }>;
  binaryParameters(doc: unknown): Promise<BinaryParameterRow[]>;
  onProgress(listener: (step: string) => void): void;
  terminate(): void;
}

type Pending = { resolve: (value: never) => void; reject: (error: Error) => void };

/** Start the engine worker. Loading begins immediately and takes several seconds. */
export function startEngine(): EngineClient {
  const worker = new Worker(new URL("./engine.worker.ts", import.meta.url), { type: "module" });
  const pending = new Map<number, Pending>();
  const listeners: ((step: string) => void)[] = [];
  let nextId = 1;
  let resolveReady!: (v: EngineInfo) => void;
  let rejectReady!: (e: Error) => void;
  const ready = new Promise<EngineInfo>((res, rej) => {
    resolveReady = res;
    rejectReady = rej;
  });

  const settle = (id: number, value: unknown, error?: string) => {
    const p = pending.get(id);
    pending.delete(id);
    if (!p) return;
    if (error !== undefined) p.reject(new Error(error));
    else p.resolve(value as never);
  };

  worker.onmessage = (event: MessageEvent<WorkerResponse>) => {
    const msg = event.data;
    switch (msg.type) {
      case "progress":
        listeners.forEach((l) => l(msg.step));
        break;
      case "ready":
        resolveReady({ version: msg.version, timings: msg.timings });
        break;
      case "failed":
        rejectReady(new Error(msg.error));
        break;
      case "result":
        settle(msg.id, { result: msg.result, ms: msg.ms });
        break;
      case "binary_parameters":
        settle(msg.id, msg.rows);
        break;
      case "error":
        settle(msg.id, undefined, msg.error);
        break;
    }
  };

  function call<T>(request: Omit<WorkerRequest, "id">): Promise<T> {
    const id = nextId++;
    return new Promise<T>((resolve, reject) => {
      pending.set(id, { resolve: resolve as (value: never) => void, reject });
      worker.postMessage({ ...request, id } as WorkerRequest);
    });
  }

  return {
    ready,
    onProgress: (listener) => listeners.push(listener),
    simulate: (doc) => call({ type: "simulate", doc }),
    binaryParameters: (doc) => call({ type: "binary_parameters", doc }),
    terminate: () => worker.terminate(),
  };
}
