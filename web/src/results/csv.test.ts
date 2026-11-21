import { describe, expect, it } from "vitest";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import type { RunResults } from "@/state/RunProvider";
import { conversion, kindOf } from "@/units/units";
import { resultsCsv } from "./csv";

const doc: Flowsheet = {
  ...emptyFlowsheet("Flash; test"),
  components: [{ id: "benzene", name: "benzene", cas: "71-43-2" }, { id: "toluene", name: "toluene", cas: "108-88-3" }],
  units: [{ id: "F-1", type: "flash" }],
  streams: [{ id: "S1", from: { unit: "FEED-1", port: "out" }, to: { unit: "F-1", port: "in" } }],
};
// Display-only numbers; real ones come from the engine.
const results: RunResults = {
  engine: "reference", engine_version: "x", converged: true,
  streams: { S1: { temperature: { value: 373.15, unit: "K" }, pressure: { value: 101325, unit: "Pa" },
    molar_flow: { value: 1, unit: "mol/s" }, vapor_fraction: { value: 0.25, unit: "1" }, mole_fractions: { benzene: 0.5, toluene: 0.5 } } },
  units: { "F-1": { duty: { value: 1500.5, unit: "W" } } },
};

const opts = (set: "SI" | "METRIC", tr: boolean) => ({
  separator: (tr ? ";" : ",") as "," | ";",
  decimal: (tr ? "," : ".") as "." | ",",
  label: (k: string) => k,
  unit: (n: string) => conversion(kindOf(n), set).unit,
  toDisplay: (n: string, v: number) => conversion(kindOf(n), set).toDisplay(v),
});

describe("results CSV", () => {
  it("writes the stream table and unit results in the unit set, with a BOM", () => {
    const csv = resultsCsv(doc, results, opts("METRIC", false));
    expect(csv.startsWith("﻿")).toBe(true);
    const lines = csv.slice(1).split("\r\n");
    expect(lines[0]).toBe("Flash; test"); // ";" is not the separator here, so no quotes
    expect(lines).toContain("flowsheet.specs.temperature,°C,100");
    expect(lines).toContain("flowsheet.specs.pressure,bar,1.01325");
    expect(lines).toContain("flowsheet.specs.molar_flow,kmol/h,3.6");
    expect(lines).toContain("x benzene,–,0.5");
    expect(lines).toContain("F-1,duty,1.5005,kW");
  });

  it("uses ; and a decimal comma for Turkish and quotes fields that contain the separator", () => {
    const csv = resultsCsv(doc, results, opts("SI", true));
    const lines = csv.slice(1).split("\r\n");
    expect(lines[0]).toBe('"Flash; test"');
    expect(lines).toContain("flowsheet.specs.temperature;K;373,15");
    expect(lines).toContain("flowsheet.specs.vapor_fraction;–;0,25");
    expect(lines).toContain("F-1;duty;1500,5;W");
  });
});
