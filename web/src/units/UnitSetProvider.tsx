import { createContext, useContext, useState, type ReactNode } from "react";
import { conversion, kindOf, UNIT_SETS, type Kind, type UnitSet } from "./units";

const KEY = "opd.unitSet";

function stored(): UnitSet {
  try {
    const v = window.localStorage.getItem(KEY);
    return (UNIT_SETS as string[]).includes(v ?? "") ? (v as UnitSet) : "SI";
  } catch {
    return "SI";
  }
}

const Ctx = createContext<{ set: UnitSet; setSet: (s: UnitSet) => void } | null>(null);

export function UnitSetProvider({ children, initial }: { children: ReactNode; initial?: UnitSet }) {
  const [set, setState] = useState<UnitSet>(() => initial ?? stored());
  const setSet = (s: UnitSet) => {
    setState(s);
    try {
      window.localStorage.setItem(KEY, s);
    } catch {
      // not kept; fine for this visit
    }
  };
  return <Ctx.Provider value={{ set, setSet }}>{children}</Ctx.Provider>;
}

/** Current unit set and helpers to show / read SI values. Defaults to SI outside a provider. */
export function useUnits() {
  const ctx = useContext(Ctx);
  const set = ctx?.set ?? "SI";
  const conv = (kindOrName: Kind | string) => conversion(KINDS.has(kindOrName) ? (kindOrName as Kind) : kindOf(kindOrName), set);
  return {
    set,
    setSet: ctx?.setSet ?? (() => {}),
    /** Display unit label for a kind or OPD name. */
    unit: (k: Kind | string) => conv(k).unit,
    digits: (k: Kind | string) => conv(k).digits,
    toDisplay: (k: Kind | string, si: number) => conv(k).toDisplay(si),
    fromDisplay: (k: Kind | string, v: number) => conv(k).fromDisplay(v),
  };
}

const KINDS = new Set<string>(["temperature", "temperature_difference", "pressure", "pressure_difference",
  "molar_flow", "power", "ua", "fraction", "number", "volume", "time", "molar_energy"]);
