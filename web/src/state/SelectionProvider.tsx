import { createContext, useContext, useState, type ReactNode } from "react";

export type Selection = { kind: "unit" | "stream"; id: string } | null;

const SelectionContext = createContext<{ selection: Selection; setSelection: (s: Selection) => void } | null>(null);

/** The selected unit or stream, shared so that results and issue lists can point at the canvas. */
export function SelectionProvider({ children }: { children: ReactNode }) {
  const [selection, setSelection] = useState<Selection>(null);
  return <SelectionContext.Provider value={{ selection, setSelection }}>{children}</SelectionContext.Provider>;
}

export function useSelection() {
  const value = useContext(SelectionContext);
  if (!value) throw new Error("useSelection must be used inside <SelectionProvider>");
  return value;
}

/** Select a unit or stream and open the flowsheet step. */
export function showOnCanvas(setSelection: (s: Selection) => void, target: Selection) {
  setSelection(target);
  window.location.hash = "#/flowsheet";
}
