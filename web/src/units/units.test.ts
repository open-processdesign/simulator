import { describe, expect, it } from "vitest";
import { conversion, kindOf, UNIT_SETS } from "./units";

describe("unit sets", () => {
  it("converts SI to display units and back exactly", () => {
    const cases: [Parameters<typeof conversion>[0], number][] = [
      ["temperature", 373.15], ["temperature_difference", 10], ["pressure", 101325], ["pressure_difference", 5e4],
      ["molar_flow", 1], ["power", 1000], ["ua", 500],
    ];
    for (const set of UNIT_SETS)
      for (const [kind, si] of cases) {
        const c = conversion(kind, set);
        expect(c.fromDisplay(c.toDisplay(si))).toBeCloseTo(si, 9);
      }
  });

  it("uses the textbook factors", () => {
    expect(conversion("temperature", "METRIC").toDisplay(373.15)).toBeCloseTo(100, 10);
    expect(conversion("temperature", "ENGLISH").toDisplay(373.15)).toBeCloseTo(212, 10);
    expect(conversion("temperature_difference", "ENGLISH").toDisplay(10)).toBeCloseTo(18, 10);
    expect(conversion("pressure", "METRIC").toDisplay(101325)).toBeCloseTo(1.01325, 10);
    expect(conversion("pressure", "ENGLISH").toDisplay(101325)).toBeCloseTo(14.696, 3);
    expect(conversion("molar_flow", "METRIC").toDisplay(1)).toBeCloseTo(3.6, 10); // kmol/h
    expect(conversion("molar_flow", "ENGLISH").toDisplay(1)).toBeCloseTo(7.9366, 4); // lbmol/h
    expect(conversion("power", "ENGLISH").toDisplay(1000)).toBeCloseTo(3412.14, 2); // Btu/h
    expect(conversion("power", "METRIC").unit).toBe("kW");
  });

  it("maps OPD names to kinds", () => {
    expect(kindOf("hot_outlet_temperature")).toBe("temperature");
    expect(kindOf("lmtd")).toBe("temperature_difference");
    expect(kindOf("pressure_drop")).toBe("pressure_difference");
    expect(kindOf("extent_2")).toBe("molar_flow");
    expect(kindOf("reboiler_duty")).toBe("power");
    expect(kindOf("split_out1")).toBe("fraction");
    expect(kindOf("stages")).toBe("number");
  });
});
