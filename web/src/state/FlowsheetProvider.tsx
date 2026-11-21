import { createContext, useContext, useEffect, useReducer, type Dispatch, type ReactNode } from "react";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { flowsheetReducer, type FlowsheetAction } from "./flowsheet";
import { loadDraft, saveDraft } from "./persistence";

const FlowsheetContext = createContext<{ doc: Flowsheet; dispatch: Dispatch<FlowsheetAction> } | null>(null);

/**
 * Holds the OPD document. Without `initial`, the last draft from this browser is restored
 * and every change is kept as the new draft (`persist`).
 */
export function FlowsheetProvider({ initial, persist = false, children }: {
  initial?: Flowsheet;
  persist?: boolean;
  children: ReactNode;
}) {
  const [doc, dispatch] = useReducer(
    flowsheetReducer,
    undefined,
    () => initial ?? (persist ? loadDraft() : null) ?? emptyFlowsheet("Untitled process"),
  );

  useEffect(() => {
    if (!persist) return;
    const timer = setTimeout(() => saveDraft(doc), 400);
    return () => clearTimeout(timer);
  }, [doc, persist]);

  return <FlowsheetContext.Provider value={{ doc, dispatch }}>{children}</FlowsheetContext.Provider>;
}

export function useFlowsheet() {
  const value = useContext(FlowsheetContext);
  if (!value) throw new Error("useFlowsheet must be used inside <FlowsheetProvider>");
  return value;
}
