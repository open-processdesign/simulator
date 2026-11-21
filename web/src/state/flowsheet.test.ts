import { describe, expect, it } from "vitest";
import { emptyFlowsheet, makeId, type Flowsheet } from "@/opd/types";
import { flowsheetReducer } from "./flowsheet";

const add = (doc: Flowsheet, name: string, cas: string) => flowsheetReducer(doc, { type: "add_component", name, cas });

describe("makeId", () => {
  it("makes schema-valid unique ids", () => {
    expect(makeId("carbon dioxide", [])).toBe("carbon_dioxide");
    expect(makeId("1,2-epoxybutane", [])).toBe("c_1_2_epoxybutane");
    expect(makeId("water", ["water"])).toBe("water_2");
    expect(makeId("çözücü", [])).toBe("cozucu");
    expect(makeId("", [])).toMatch(/^[A-Za-z][A-Za-z0-9_-]*$/);
  });
});

describe("flowsheetReducer", () => {
  it("adds components once per CAS number", () => {
    let doc = add(emptyFlowsheet("x"), "benzene", "71-43-2");
    doc = add(doc, "benzene", "71-43-2");
    doc = add(doc, "toluene", "108-88-3");
    expect(doc.components.map((c) => c.id)).toEqual(["benzene", "toluene"]);
  });

  it("removing a component also removes its binary parameters and composition entries", () => {
    let doc = add(add(add(emptyFlowsheet("x"), "benzene", "71-43-2"), "toluene", "108-88-3"), "water", "7732-18-5");
    doc = flowsheetReducer(doc, { type: "set_kij", i: "benzene", j: "toluene", value: 0.01 });
    doc = flowsheetReducer(doc, { type: "set_kij", i: "toluene", j: "water", value: 0.2 });
    doc = {
      ...doc,
      streams: [{ id: "S1", from: { unit: "A", port: "out" }, to: { unit: "B", port: "in" },
        state: { mole_fractions: { benzene: 0.5, toluene: 0.5 } } }],
    };
    doc = flowsheetReducer(doc, { type: "remove_component", id: "benzene" });
    expect(doc.components.map((c) => c.id)).toEqual(["toluene", "water"]);
    expect(doc.thermo.binary_parameters).toEqual([{ i: "toluene", j: "water", name: "kij", value: 0.2, source: "user" }]);
    expect(doc.streams[0].state?.mole_fractions).toEqual({ toluene: 0.5 });
  });

  it("sets, replaces and clears a user k_ij regardless of pair order", () => {
    let doc = add(add(emptyFlowsheet("x"), "benzene", "71-43-2"), "toluene", "108-88-3");
    doc = flowsheetReducer(doc, { type: "set_kij", i: "benzene", j: "toluene", value: 0.01 });
    doc = flowsheetReducer(doc, { type: "set_kij", i: "toluene", j: "benzene", value: 0.02 });
    expect(doc.thermo.binary_parameters).toEqual([{ i: "toluene", j: "benzene", name: "kij", value: 0.02, source: "user" }]);
    doc = flowsheetReducer(doc, { type: "clear_kij", i: "benzene", j: "toluene" });
    expect(doc.thermo.binary_parameters).toEqual([]);
  });

  it("sets the property package", () => {
    expect(flowsheetReducer(emptyFlowsheet("x"), { type: "set_package", package: "SRK" }).thermo.package).toBe("SRK");
  });
});
