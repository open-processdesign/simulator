import { makeId, type BinaryParameter, type Flowsheet, type ThermoPackage } from "@/opd/types";

export type FlowsheetAction =
  | { type: "add_component"; name: string; cas: string; formula?: string }
  | { type: "remove_component"; id: string }
  | { type: "set_package"; package: ThermoPackage }
  | { type: "set_kij"; i: string; j: string; value: number }
  | { type: "clear_kij"; i: string; j: string }
  | { type: "replace"; doc: Flowsheet };

const samePair = (p: BinaryParameter, i: string, j: string) =>
  (p.i === i && p.j === j) || (p.i === j && p.j === i);

/** Pure reducer over the OPD document; the UI never edits the document any other way. */
export function flowsheetReducer(doc: Flowsheet, action: FlowsheetAction): Flowsheet {
  switch (action.type) {
    case "add_component": {
      if (doc.components.some((c) => c.cas === action.cas)) return doc;
      const id = makeId(action.name, doc.components.map((c) => c.id));
      const component = { id, name: action.name, cas: action.cas, ...(action.formula ? { formula: action.formula } : {}) };
      return { ...doc, components: [...doc.components, component] };
    }
    case "remove_component": {
      const { id } = action;
      return {
        ...doc,
        components: doc.components.filter((c) => c.id !== id),
        thermo: {
          ...doc.thermo,
          binary_parameters: (doc.thermo.binary_parameters ?? []).filter((p) => p.i !== id && p.j !== id),
        },
        // Compositions that mention the component lose that entry; the engine then reports
        // fractions that no longer add up to 1 on the affected stream.
        streams: doc.streams.map((s) => {
          if (!s.state?.mole_fractions || !(id in s.state.mole_fractions)) return s;
          const { [id]: _removed, ...rest } = s.state.mole_fractions;
          return { ...s, state: { ...s.state, mole_fractions: rest } };
        }),
      };
    }
    case "set_package":
      return { ...doc, thermo: { ...doc.thermo, package: action.package } };
    case "set_kij": {
      const others = (doc.thermo.binary_parameters ?? []).filter(
        (p) => !(p.name.toLowerCase() === "kij" && samePair(p, action.i, action.j)),
      );
      const param: BinaryParameter = { i: action.i, j: action.j, name: "kij", value: action.value, source: "user" };
      return { ...doc, thermo: { ...doc.thermo, binary_parameters: [...others, param] } };
    }
    case "clear_kij":
      return {
        ...doc,
        thermo: {
          ...doc.thermo,
          binary_parameters: (doc.thermo.binary_parameters ?? []).filter(
            (p) => !(p.name.toLowerCase() === "kij" && samePair(p, action.i, action.j)),
          ),
        },
      };
    case "replace":
      return action.doc;
  }
}
