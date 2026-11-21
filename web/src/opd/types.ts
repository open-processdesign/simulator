/**
 * TypeScript view of the OPD flowsheet format v0.1 (source of truth:
 * schema/flowsheet.schema.json). All quantities are SI.
 */
export interface Quantity {
  value: number;
  unit: string;
}

export interface Component {
  id: string;
  name: string;
  cas: string;
  formula?: string;
}

export type ThermoPackage = "IDEAL" | "PR" | "SRK" | "NRTL" | "UNIQUAC" | "UNIFAC";
export type ParameterSource = "database" | "user" | "literature" | "regression" | "default";

export interface BinaryParameter {
  i: string;
  j: string;
  name: string;
  value: number;
  source: ParameterSource;
  reference?: string;
}

export interface Thermo {
  package: ThermoPackage;
  binary_parameters?: BinaryParameter[];
}

export interface Unit {
  id: string;
  type: string;
  label?: string;
  specs?: Record<string, Quantity>;
  options?: Record<string, unknown>;
}

export interface StreamState {
  temperature?: Quantity;
  pressure?: Quantity;
  molar_flow?: Quantity;
  vapor_fraction?: Quantity;
  mole_fractions?: Record<string, number>;
}

export interface Stream {
  id: string;
  label?: string;
  from: { unit: string; port: string };
  to: { unit: string; port: string };
  state?: StreamState;
}

export interface Flowsheet {
  format: "opd-flowsheet";
  version: "0.1";
  name: string;
  description?: string;
  components: Component[];
  thermo: Thermo;
  units: Unit[];
  streams: Stream[];
  results?: Record<string, unknown>;
  layout?: Record<string, { x: number; y: number }>;
}

export function emptyFlowsheet(name: string): Flowsheet {
  return {
    format: "opd-flowsheet",
    version: "0.1",
    name,
    components: [],
    thermo: { package: "PR" },
    units: [],
    streams: [],
  };
}

const ID_PATTERN = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;

/** A readable, schema-valid, unique id from a component name ("carbon dioxide" → "carbon_dioxide"). */
export function makeId(name: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  let base = name
    .replace(/ı/g, "i")
    .replace(/İ/g, "I")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 56);
  if (!/^[A-Za-z]/.test(base)) base = `c_${base}`;
  if (!ID_PATTERN.test(base)) base = "component";
  let id = base;
  for (let n = 2; used.has(id); n++) id = `${base}_${n}`;
  return id;
}
