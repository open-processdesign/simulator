import { unitDef } from "@/flowsheet/catalog";
import { makeId, type BinaryParameter, type Flowsheet, type Quantity, type StreamState, type ThermoPackage } from "@/opd/types";

type StateField = "temperature" | "pressure" | "molar_flow" | "vapor_fraction";
type Endpoint = { unit: string; port: string };

export type FlowsheetAction =
  | { type: "add_component"; name: string; cas: string; formula?: string }
  | { type: "remove_component"; id: string }
  | { type: "set_package"; package: ThermoPackage }
  | { type: "set_kij"; i: string; j: string; value: number }
  | { type: "clear_kij"; i: string; j: string }
  | { type: "replace"; doc: Flowsheet }
  | { type: "add_unit"; unitType: string; x: number; y: number }
  | { type: "remove_unit"; id: string }
  | { type: "move_unit"; id: string; x: number; y: number }
  | { type: "set_label"; id: string; label: string }
  | { type: "set_options"; id: string; options: Record<string, unknown> }
  | { type: "set_spec"; id: string; name: string; quantity: Quantity | null; exclusive?: string[] }
  | { type: "connect"; from: Endpoint; to: Endpoint }
  | { type: "remove_stream"; id: string }
  | { type: "set_stream_state"; id: string; field: StateField; quantity: Quantity | null; exclusive?: StateField[] }
  | { type: "set_composition"; id: string; fractions: Record<string, number> | null };

/** Next free id of the form `${prefix}-${n}` / `${prefix}${n}`. */
export function nextId(prefix: string, taken: Iterable<string>, separator = "-"): string {
  const used = new Set(taken);
  for (let n = 1; ; n++) if (!used.has(`${prefix}${separator}${n}`)) return `${prefix}${separator}${n}`;
}

/** Can a stream go from `from` to `to`? (outlet → inlet, both free, different units) */
export function canConnect(doc: Flowsheet, from: Endpoint, to: Endpoint): boolean {
  if (from.unit === to.unit) return false;
  const src = doc.units.find((u) => u.id === from.unit);
  const dst = doc.units.find((u) => u.id === to.unit);
  if (!src || !dst) return false;
  if (!unitDef(src.type)?.outlets.includes(from.port) || !unitDef(dst.type)?.inlets.includes(to.port)) return false;
  return !doc.streams.some(
    (s) => (s.from.unit === from.unit && s.from.port === from.port) || (s.to.unit === to.unit && s.to.port === to.port),
  );
}

function mapUnit(doc: Flowsheet, id: string, f: (u: Flowsheet["units"][number]) => Flowsheet["units"][number]): Flowsheet {
  return { ...doc, units: doc.units.map((u) => (u.id === id ? f(u) : u)) };
}

function mapStreamState(doc: Flowsheet, id: string, f: (s: StreamState) => StreamState): Flowsheet {
  return { ...doc, streams: doc.streams.map((s) => (s.id === id ? { ...s, state: f(s.state ?? {}) } : s)) };
}

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
    case "add_unit": {
      const def = unitDef(action.unitType);
      if (!def) return doc;
      const id = nextId(def.prefix, doc.units.map((u) => u.id));
      return {
        ...doc,
        units: [...doc.units, { id, type: action.unitType }],
        layout: { ...doc.layout, [id]: { x: action.x, y: action.y } },
      };
    }
    case "remove_unit": {
      const { [action.id]: _gone, ...layout } = doc.layout ?? {};
      return {
        ...doc,
        units: doc.units.filter((u) => u.id !== action.id),
        streams: doc.streams.filter((s) => s.from.unit !== action.id && s.to.unit !== action.id),
        layout,
      };
    }
    case "move_unit":
      return { ...doc, layout: { ...doc.layout, [action.id]: { x: action.x, y: action.y } } };
    case "set_label":
      return mapUnit(doc, action.id, (u) => {
        const { label: _old, ...rest } = u;
        return action.label.trim() ? { ...rest, label: action.label.trim() } : rest;
      });
    case "set_options":
      return mapUnit(doc, action.id, (u) => ({ ...u, options: { ...u.options, ...action.options } }));
    case "set_spec":
      return mapUnit(doc, action.id, (u) => {
        const specs = { ...u.specs };
        for (const name of action.exclusive ?? []) delete specs[name];
        delete specs[action.name];
        if (action.quantity) specs[action.name] = action.quantity;
        return { ...u, specs };
      });
    case "connect": {
      if (!canConnect(doc, action.from, action.to)) return doc;
      const id = nextId("S", doc.streams.map((s) => s.id), "");
      return { ...doc, streams: [...doc.streams, { id, from: action.from, to: action.to }] };
    }
    case "remove_stream":
      return { ...doc, streams: doc.streams.filter((s) => s.id !== action.id) };
    case "set_stream_state":
      return mapStreamState(doc, action.id, (st) => {
        const next = { ...st };
        for (const name of action.exclusive ?? []) delete next[name];
        delete next[action.field];
        if (action.quantity) next[action.field] = action.quantity;
        return next;
      });
    case "set_composition":
      return mapStreamState(doc, action.id, (st) => {
        const { mole_fractions: _old, ...rest } = st;
        return action.fractions ? { ...rest, mole_fractions: action.fractions } : rest;
      });
  }
}
