import { describe, expect, it } from "vitest";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { canConnect, flowsheetReducer as r, nextId } from "./flowsheet";

function build(): Flowsheet {
  let doc = emptyFlowsheet("x");
  doc = r(doc, { type: "add_unit", unitType: "feed", x: 0, y: 0 });
  doc = r(doc, { type: "add_unit", unitType: "flash", x: 200, y: 0 });
  doc = r(doc, { type: "add_unit", unitType: "product", x: 400, y: -50 });
  doc = r(doc, { type: "add_unit", unitType: "product", x: 400, y: 50 });
  return doc;
}

describe("flowsheet editing", () => {
  it("adds units with readable ids and layout", () => {
    const doc = build();
    expect(doc.units.map((u) => u.id)).toEqual(["FEED-1", "F-1", "PROD-1", "PROD-2"]);
    expect(doc.layout?.["F-1"]).toEqual({ x: 200, y: 0 });
    expect(r(doc, { type: "add_unit", unitType: "nope", x: 0, y: 0 })).toBe(doc);
  });

  it("connects outlet → inlet once per port and names streams S1, S2, …", () => {
    let doc = build();
    doc = r(doc, { type: "connect", from: { unit: "FEED-1", port: "out" }, to: { unit: "F-1", port: "in" } });
    doc = r(doc, { type: "connect", from: { unit: "F-1", port: "vapor" }, to: { unit: "PROD-1", port: "in" } });
    expect(doc.streams.map((s) => s.id)).toEqual(["S1", "S2"]);
    // Port already used, wrong direction, same unit, unknown port: all refused.
    expect(canConnect(doc, { unit: "F-1", port: "vapor" }, { unit: "PROD-2", port: "in" })).toBe(false);
    expect(canConnect(doc, { unit: "PROD-2", port: "in" }, { unit: "F-1", port: "in" })).toBe(false);
    expect(canConnect(doc, { unit: "F-1", port: "liquid" }, { unit: "F-1", port: "in" })).toBe(false);
    expect(canConnect(doc, { unit: "F-1", port: "bottom" }, { unit: "PROD-2", port: "in" })).toBe(false);
    expect(canConnect(doc, { unit: "F-1", port: "liquid" }, { unit: "PROD-2", port: "in" })).toBe(true);
  });

  it("removing a unit removes its streams and position", () => {
    let doc = build();
    doc = r(doc, { type: "connect", from: { unit: "FEED-1", port: "out" }, to: { unit: "F-1", port: "in" } });
    doc = r(doc, { type: "remove_unit", id: "F-1" });
    expect(doc.units.map((u) => u.id)).toEqual(["FEED-1", "PROD-1", "PROD-2"]);
    expect(doc.streams).toEqual([]);
    expect(doc.layout?.["F-1"]).toBeUndefined();
  });

  it("sets exclusive specs, labels and feed state", () => {
    let doc = build();
    doc = r(doc, { type: "set_spec", id: "F-1", name: "temperature", quantity: { value: 368.15, unit: "K" } });
    doc = r(doc, { type: "set_spec", id: "F-1", name: "duty", quantity: { value: 0, unit: "W" }, exclusive: ["temperature", "vapor_fraction"] });
    expect(doc.units[1].specs).toEqual({ duty: { value: 0, unit: "W" } });
    doc = r(doc, { type: "set_spec", id: "F-1", name: "duty", quantity: null });
    expect(doc.units[1].specs).toEqual({});
    doc = r(doc, { type: "set_label", id: "F-1", label: "  Flash drum " });
    expect(doc.units[1].label).toBe("Flash drum");
    doc = r(doc, { type: "set_label", id: "F-1", label: "" });
    expect(doc.units[1].label).toBeUndefined();

    doc = r(doc, { type: "connect", from: { unit: "FEED-1", port: "out" }, to: { unit: "F-1", port: "in" } });
    doc = r(doc, { type: "set_stream_state", id: "S1", field: "temperature", quantity: { value: 350, unit: "K" } });
    doc = r(doc, { type: "set_stream_state", id: "S1", field: "vapor_fraction", quantity: { value: 0, unit: "1" }, exclusive: ["temperature"] });
    doc = r(doc, { type: "set_composition", id: "S1", fractions: { a: 0.5, b: 0.5 } });
    expect(doc.streams[0].state).toEqual({ vapor_fraction: { value: 0, unit: "1" }, mole_fractions: { a: 0.5, b: 0.5 } });
  });

  it("nextId fills gaps", () => {
    expect(nextId("F", ["F-1", "F-3"])).toBe("F-2");
    expect(nextId("S", ["S1"], "")).toBe("S2");
  });
});
