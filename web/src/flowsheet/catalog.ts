/**
 * Unit catalogue for the canvas. Ports and spec groups follow the reference engine's
 * conventions (DECISIONS.md D013); the engine remains the judge of what is complete.
 */
export type Category = "io" | "mixing" | "separation" | "heat" | "pressure" | "reaction";

/** Spec group: the user gives exactly one of `options` (or none if `optional`). */
export interface SpecGroup {
  key: string; // i18n key under flowsheet.groups
  options: string[]; // spec names
  optional?: boolean;
}

export interface UnitDef {
  type: string;
  category: Category;
  prefix: string; // id prefix, e.g. "F" → F-1
  inlets: string[];
  outlets: string[];
  groups: SpecGroup[];
  available: boolean; // supported by the demo engine
}

const PRESSURE_REQUIRED: SpecGroup = { key: "outlet_pressure", options: ["pressure", "pressure_drop"] };
const PRESSURE_OPTIONAL: SpecGroup = { ...PRESSURE_REQUIRED, optional: true };
const THERMAL: SpecGroup = { key: "thermal", options: ["temperature", "duty", "vapor_fraction"] };
const PRESSURE_UP: SpecGroup = { key: "pressure_up", options: ["pressure", "pressure_increase"] };
const EFFICIENCY: SpecGroup = { key: "efficiency", options: ["efficiency"], optional: true };

export const UNITS: UnitDef[] = [
  { type: "feed", category: "io", prefix: "FEED", inlets: [], outlets: ["out"], groups: [], available: true },
  { type: "product", category: "io", prefix: "PROD", inlets: ["in"], outlets: [], groups: [], available: true },
  { type: "mixer", category: "mixing", prefix: "M", inlets: ["in1", "in2", "in3"], outlets: ["out"],
    groups: [{ key: "mixer_pressure", options: ["pressure"], optional: true }], available: true },
  { type: "splitter", category: "mixing", prefix: "SP", inlets: ["in"], outlets: ["out1", "out2", "out3"], groups: [], available: true },
  { type: "flash", category: "separation", prefix: "F", inlets: ["in"], outlets: ["vapor", "liquid"], groups: [PRESSURE_REQUIRED, THERMAL], available: true },
  { type: "heater", category: "heat", prefix: "H", inlets: ["in"], outlets: ["out"], groups: [THERMAL, PRESSURE_OPTIONAL], available: true },
  { type: "valve", category: "pressure", prefix: "V", inlets: ["in"], outlets: ["out"], groups: [PRESSURE_REQUIRED], available: true },
  { type: "heat_exchanger", category: "heat", prefix: "E", inlets: ["hot_in", "cold_in"], outlets: ["hot_out", "cold_out"],
    groups: [
      { key: "hx_spec", options: ["hot_outlet_temperature", "cold_outlet_temperature", "duty"] },
      { key: "hot_dp", options: ["hot_pressure_drop"], optional: true },
      { key: "cold_dp", options: ["cold_pressure_drop"], optional: true },
    ], available: true },
  { type: "pump", category: "pressure", prefix: "P", inlets: ["in"], outlets: ["out"], groups: [PRESSURE_UP, EFFICIENCY], available: true },
  { type: "compressor", category: "pressure", prefix: "C", inlets: ["in"], outlets: ["out"], groups: [PRESSURE_UP, EFFICIENCY], available: true },
  { type: "conversion_reactor", category: "reaction", prefix: "R", inlets: ["in"], outlets: ["out"],
    groups: [{ key: "reactor_thermal", options: ["temperature", "duty"] }, PRESSURE_OPTIONAL], available: true },
  { type: "shortcut_column", category: "separation", prefix: "T", inlets: ["in"], outlets: ["distillate", "bottoms"],
    groups: [
      { key: "lk_recovery", options: ["lk_recovery"] },
      { key: "hk_recovery", options: ["hk_recovery"] },
      { key: "reflux", options: ["reflux_ratio_factor"] },
      { key: "column_pressure", options: ["pressure"], optional: true },
    ], available: true },
];

export const CATEGORIES: Category[] = ["io", "mixing", "separation", "heat", "pressure", "reaction"];

export function unitDef(type: string): UnitDef | undefined {
  return UNITS.find((u) => u.type === type);
}

/** SI unit and input step per spec / state field (DECISIONS.md D007). */
export const SPEC_UNITS: Record<string, string> = {
  temperature: "K",
  pressure: "Pa",
  pressure_drop: "Pa",
  duty: "W",
  vapor_fraction: "1",
  molar_flow: "mol/s",
  pressure_increase: "Pa",
  efficiency: "1",
  hot_outlet_temperature: "K",
  cold_outlet_temperature: "K",
  hot_pressure_drop: "Pa",
  cold_pressure_drop: "Pa",
  lk_recovery: "1",
  hk_recovery: "1",
  reflux_ratio_factor: "1",
};

export function specUnit(name: string): string {
  return SPEC_UNITS[name] ?? (name.startsWith("split_") ? "1" : "");
}
