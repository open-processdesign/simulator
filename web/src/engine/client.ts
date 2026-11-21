import type { EngineResult, Timing } from "./bootstrap";
import type { WorkerRequest, WorkerResponse } from "./protocol";

export interface EngineClient {
  /** Resolves once Python, the packages and the engine are loaded. */
  ready: Promise<{ version: string; timings: Timing[] }>;
  simulate(doc: unknown): Promise<{ result: EngineResult; ms: number }>;
  onProgress(listener: (step: string) => void): void;
  terminate(): void;
}

/** Start the engine worker. Loading begins immediately and takes several seconds. */
export function startEngine(): EngineClient {
  const worker = new Worker(new URL("./engine.worker.ts", import.meta.url), { type: "module" });
  const pending = new Map<number, { resolve: (v: { result: EngineResult; ms: number }) => void; reject: (e: Error) => void }>();
  const listeners: ((step: string) => void)[] = [];
  let nextId = 1;
  let resolveReady!: (v: { version: string; timings: Timing[] }) => void;
  let rejectReady!: (e: Error) => void;
  const ready = new Promise<{ version: string; timings: Timing[] }>((res, rej) => {
    resolveReady = res;
    rejectReady = rej;
  });

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
        pending.get(msg.id)?.resolve({ result: msg.result, ms: msg.ms });
        pending.delete(msg.id);
        break;
      case "error":
        pending.get(msg.id)?.reject(new Error(msg.error));
        pending.delete(msg.id);
        break;
    }
  };

  return {
    ready,
    onProgress: (listener) => listeners.push(listener),
    simulate(doc) {
      const id = nextId++;
      const request: WorkerRequest = { id, type: "simulate", doc };
      return new Promise((resolve, reject) => {
        pending.set(id, { resolve, reject });
        worker.postMessage(request);
      });
    },
    terminate: () => worker.terminate(),
  };
}
