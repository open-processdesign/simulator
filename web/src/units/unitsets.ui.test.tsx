import { beforeEach, describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { SidePanel } from "@/flowsheet/SidePanel";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { renderWithApp } from "@/test/render";
import { StreamTable } from "@/results/StreamTable";
import { UnitSetProvider } from "./UnitSetProvider";

const doc: Flowsheet = {
  ...emptyFlowsheet("t"),
  components: [{ id: "water", name: "water", cas: "7732-18-5" }],
  units: [{ id: "FEED-1", type: "feed" }, { id: "H-1", type: "heater", specs: { pressure_drop: { value: 20000, unit: "Pa" } } }],
  streams: [{ id: "S1", from: { unit: "FEED-1", port: "out" }, to: { unit: "H-1", port: "in" } }],
};

function DocProbe() {
  const { doc: d } = useFlowsheet();
  return <pre data-testid="doc">{JSON.stringify(d)}</pre>;
}
const current = () => JSON.parse(screen.getByTestId("doc").textContent ?? "{}") as Flowsheet;

describe("unit sets in the UI", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("reads inputs in metric units and stores SI", async () => {
    const user = userEvent.setup();
    renderWithApp(
      <UnitSetProvider initial="METRIC">
        <SidePanel selection={{ kind: "unit", id: "FEED-1" }} issues={null} onDeleted={() => {}} />
        <DocProbe />
      </UnitSetProvider>,
      doc,
    );
    const feed = screen.getByRole("group", { name: /Feed conditions/ });
    expect(within(feed).getByText("°C")).toBeInTheDocument();
    await user.type(within(feed).getByRole("textbox", { name: "Temperature" }), "25{Enter}");
    await user.type(within(feed).getByRole("textbox", { name: "Pressure" }), "1,01325{Enter}");
    await user.type(within(feed).getByRole("textbox", { name: "Molar flow" }), "36{Enter}");
    const st = current().streams[0].state!;
    expect(st.temperature).toEqual({ value: 298.15, unit: "K" });
    expect(st.pressure!.value).toBeCloseTo(101325, 6);
    expect(st.molar_flow!.value).toBeCloseTo(10, 10); // 36 kmol/h = 10 mol/s
    expect(st.pressure!.unit).toBe("Pa");
  });

  it("shows SI values converted, e.g. a pressure drop in psi", () => {
    renderWithApp(
      <UnitSetProvider initial="ENGLISH">
        <SidePanel selection={{ kind: "unit", id: "H-1" }} issues={null} onDeleted={() => {}} />
      </UnitSetProvider>,
      doc,
    );
    const group = screen.getByRole("group", { name: "Outlet pressure" });
    expect(within(group).getByRole("textbox", { name: "Pressure drop" })).toHaveValue("2.9007547546");
    expect(within(group).getByText("psi")).toBeInTheDocument();
  });

  it("stream table uses the unit set", () => {
    renderWithApp(
      <UnitSetProvider initial="METRIC">
        <StreamTable doc={doc} results={{ engine: "x", engine_version: "x", converged: true, units: {},
          streams: { S1: { temperature: { value: 373.15, unit: "K" }, pressure: { value: 200000, unit: "Pa" },
            molar_flow: { value: 1, unit: "mol/s" }, vapor_fraction: { value: 0, unit: "1" }, mole_fractions: { water: 1 } } } }} />
      </UnitSetProvider>,
      doc,
    );
    const table = screen.getByRole("table");
    const row = (label: string) => within(table).getByRole("row", { name: new RegExp(`^${label}`) });
    expect(within(row("Temperature")).getAllByRole("cell").map((c) => c.textContent)).toEqual(["°C", "100.00"]);
    expect(within(row("Pressure")).getAllByRole("cell").map((c) => c.textContent)).toEqual(["bar", "2.0000"]);
    expect(within(row("Molar flow")).getAllByRole("cell").map((c) => c.textContent)).toEqual(["kmol/h", "3.600"]);
  });
});
