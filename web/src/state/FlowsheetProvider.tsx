import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from "react";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { flowsheetReducer, type FlowsheetAction } from "./flowsheet";

const FlowsheetContext = createContext<{ doc: Flowsheet; dispatch: Dispatch<FlowsheetAction> } | null>(null);

export function FlowsheetProvider({ initial, children }: { initial?: Flowsheet; children: ReactNode }) {
  const [doc, dispatch] = useReducer(flowsheetReducer, initial ?? emptyFlowsheet("Untitled process"));
  return <FlowsheetContext.Provider value={{ doc, dispatch }}>{children}</FlowsheetContext.Provider>;
}

export function useFlowsheet() {
  const value = useContext(FlowsheetContext);
  if (!value) throw new Error("useFlowsheet must be used inside <FlowsheetProvider>");
  return value;
}
