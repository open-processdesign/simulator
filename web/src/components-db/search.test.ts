import { describe, expect, it } from "vitest";
import { COMPONENTS, searchComponents } from "./search";

describe("component search", () => {
  it("has the engine-ready component index", () => {
    expect(COMPONENTS.length).toBeGreaterThan(1000);
  });

  it("finds by name, with exact matches first", () => {
    expect(searchComponents("benzene")[0]).toMatchObject({ name: "benzene", cas: "71-43-2" });
    expect(searchComponents("BENZ").length).toBeGreaterThan(3);
  });

  it("finds by CAS number, formula and synonym", () => {
    expect(searchComponents("108-88-3")[0].name).toBe("toluene");
    expect(searchComponents("C7H8").map((c) => c.name)).toContain("toluene");
    expect(searchComponents("propylene").map((c) => c.name)).toContain("propene");
  });

  it("returns nothing for an empty query and respects the limit", () => {
    expect(searchComponents("  ")).toEqual([]);
    expect(searchComponents("a", 5)).toHaveLength(5);
  });
});
