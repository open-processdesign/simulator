import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { startEngine, type EngineClient } from "./client";

export type EngineStatus =
  | { state: "loading"; step: string }
  | { state: "ready"; version: string }
  | { state: "failed"; error: string };

const EngineContext = createContext<{ status: EngineStatus; client: EngineClient | null }>({
  status: { state: "loading", step: "" },
  client: null,
});

/**
 * Starts the in-browser engine as soon as the app opens (DECISIONS.md D014) and shares
 * its status. `create` replaces the Web Worker in tests.
 */
export function EngineProvider({ children, create = startEngine }: { children: ReactNode; create?: () => EngineClient }) {
  const [client, setClient] = useState<EngineClient | null>(null);
  const [status, setStatus] = useState<EngineStatus>({ state: "loading", step: "" });

  useEffect(() => {
    let alive = true;
    const engine = create();
    setClient(engine);
    engine.onProgress((step) => alive && setStatus({ state: "loading", step }));
    engine.ready
      .then((info) => alive && setStatus({ state: "ready", version: info.version }))
      .catch((error: Error) => alive && setStatus({ state: "failed", error: error.message }));
    return () => {
      alive = false;
      engine.terminate();
    };
  }, [create]);

  return <EngineContext.Provider value={{ status, client }}>{children}</EngineContext.Provider>;
}

export function useEngine() {
  return useContext(EngineContext);
}
