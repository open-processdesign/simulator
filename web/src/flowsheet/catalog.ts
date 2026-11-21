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

export const UNITS: UnitDef[] = [
  { type: "feed", category: "io", prefix: "FEED", inlets: [], outlets: ["out"], groups: [], available: true },
  { type: "product", category: "io", prefix: "PROD", inlets: ["in"], outlets: [], groups: [], available: true },
  { type: "mixer", category: "mixing", prefix: "M", inlets: ["in1", "in2", "in3"], outlets: ["out"],
    groups: [{ key: "mixer_pressure", options: ["pressure"], optional: true }], available: true },
  { type: "splitter", category: "mixing", prefix: "SP", inlets: ["in"], outlets: ["out1", "out2", "out3"], groups: [], available: true },
  { type: "flash", category: "separation", prefix: "F", inlets: ["in"], outlets: ["vapor", "liquid"], groups: [PRESSURE_REQUIRED, THERMAL], available: true },
  { type: "heater", category: "heat", prefix: "H", inlets: ["in"], outlets: ["out"], groups: [THERMAL, PRESSURE_OPTIONAL], available: true },
  { type: "valve", category: "pressure", prefix: "V", inlets: ["in"], outlets: ["out"], groups: [PRESSURE_REQUIRED], available: true },
  // Coming with T09 (reference engine units from textbooks):
  { type: "heat_exchanger", category: "heat", prefix: "E", inlets: ["hot_in", "cold_in"], outlets: ["hot_out", "cold_out"], groups: [], available: false },
  { type: "pump", category: "pressure", prefix: "P", inlets: ["in"], outlets: ["out"], groups: [], available: false },
  { type: "compressor", category: "pressure", prefix: "C", inlets: ["in"], outlets: ["out"], groups: [], available: false },
  { type: "conversion_reactor", category: "reaction", prefix: "R", inlets: ["in"], outlets: ["out"], groups: [], available: false },
  { type: "shortcut_column", category: "separation", prefix: "T", inlets: ["in"], outlets: ["distillate", "bottoms"], groups: [], available: false },
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
};

export function specUnit(name: string): string {
  return SPEC_UNITS[name] ?? (name.startsWith("split_") ? "1" : "");
}
