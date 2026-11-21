/**
 * Unit sets for display and input. Documents and the engine always use SI (DECISIONS.md D007);
 * conversion happens only here, at the UI edge.
 */
export type UnitSet = "SI" | "METRIC" | "ENGLISH";
export const UNIT_SETS: UnitSet[] = ["SI", "METRIC", "ENGLISH"];

export type Kind =
  | "temperature" | "temperature_difference" | "pressure" | "pressure_difference"
  | "molar_flow" | "power" | "ua" | "fraction" | "number" | "volume" | "time" | "molar_energy";

type Conversion = { unit: string; toDisplay: (si: number) => number; fromDisplay: (v: number) => number; digits: number };

const id = (unit: string, digits: number): Conversion => ({ unit, toDisplay: (v) => v, fromDisplay: (v) => v, digits });
const scale = (unit: string, factor: number, digits: number): Conversion => ({
  unit, toDisplay: (v) => v * factor, fromDisplay: (v) => v / factor, digits });

const PSI = 6894.757293168; // Pa per psi
const LBMOL = 453.59237; // mol per lbmol
const BTU_H = 3.412141633; // Btu/h per W (IT Btu)

const TABLE: Record<Kind, Record<UnitSet, Conversion>> = {
  temperature: {
    SI: id("K", 2),
    METRIC: { unit: "°C", toDisplay: (k) => k - 273.15, fromDisplay: (c) => c + 273.15, digits: 2 },
    ENGLISH: { unit: "°F", toDisplay: (k) => k * 1.8 - 459.67, fromDisplay: (f) => (f + 459.67) / 1.8, digits: 2 },
  },
  temperature_difference: { SI: id("K", 2), METRIC: id("°C", 2), ENGLISH: scale("°F", 1.8, 2) },
  pressure: { SI: id("Pa", 0), METRIC: scale("bar", 1e-5, 4), ENGLISH: scale("psia", 1 / PSI, 3) },
  pressure_difference: { SI: id("Pa", 0), METRIC: scale("bar", 1e-5, 4), ENGLISH: scale("psi", 1 / PSI, 3) },
  molar_flow: { SI: id("mol/s", 4), METRIC: scale("kmol/h", 3.6, 3), ENGLISH: scale("lbmol/h", 3600 / LBMOL, 3) },
  power: { SI: id("W", 0), METRIC: scale("kW", 1e-3, 2), ENGLISH: scale("Btu/h", BTU_H, 0) },
  ua: { SI: id("W/K", 1), METRIC: scale("kW/K", 1e-3, 3), ENGLISH: scale("Btu/(h·°F)", BTU_H / 1.8, 1) },
  volume: { SI: id("m³", 4), METRIC: id("m³", 4), ENGLISH: scale("ft³", 35.31466672, 3) },
  time: { SI: id("s", 2), METRIC: id("s", 2), ENGLISH: id("s", 2) },
  molar_energy: { SI: id("J/mol", 0), METRIC: scale("kJ/mol", 1e-3, 3), ENGLISH: scale("Btu/lbmol", 0.429922614, 1) },
  fraction: { SI: id("–", 4), METRIC: id("–", 4), ENGLISH: id("–", 4) },
  number: { SI: id("–", 2), METRIC: id("–", 2), ENGLISH: id("–", 2) },
};

const KIND_BY_NAME: Record<string, Kind> = {
  temperature: "temperature",
  hot_outlet_temperature: "temperature",
  cold_outlet_temperature: "temperature",
  isentropic_temperature: "temperature",
  approach_hot_end: "temperature_difference",
  approach_cold_end: "temperature_difference",
  lmtd: "temperature_difference",
  minimum_approach: "temperature_difference",
  mean_temperature_difference: "temperature_difference",
  zones: "number",
  pressure: "pressure",
  pressure_drop: "pressure_difference",
  pressure_increase: "pressure_difference",
  hot_pressure_drop: "pressure_difference",
  cold_pressure_drop: "pressure_difference",
  molar_flow: "molar_flow",
  duty: "power",
  power: "power",
  condenser_duty: "power",
  reboiler_duty: "power",
  ua: "ua",
  minimum_stages: "number",
  stages: "number",
  feed_stage: "number",
  minimum_reflux_ratio: "number",
  reflux_ratio: "number",
  relative_volatility: "number",
  number_of_stages: "number",
  reflux_rate: "molar_flow",
  boilup_rate: "molar_flow",
  distillate_rate: "molar_flow",
  top_temperature: "temperature",
  bottom_temperature: "temperature",
  iterations: "number",
  volume: "volume",
  space_time: "time",
  activation_energy: "molar_energy",
  rate_constant: "number",
  order: "number",
};

/** Kind of a spec, state field or result by its OPD name (unknown names are dimensionless). */
export function kindOf(name: string): Kind {
  if (name.startsWith("extent_")) return "molar_flow";
  if (name.startsWith("equilibrium_constant_")) return "number";
  return KIND_BY_NAME[name] ?? "fraction";
}

export function conversion(kind: Kind, set: UnitSet): Conversion {
  return TABLE[kind][set];
}
