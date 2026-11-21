import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import type { EngineIssue } from "@/engine/bootstrap";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { fakeEngine, renderWithApp } from "@/test/render";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { FlowsheetPage } from "./FlowsheetPage";
import { SidePanel } from "./SidePanel";

const flashDrum = (): Flowsheet => ({
  ...emptyFlowsheet("t"),
  components: [
    { id: "benzene", name: "benzene", cas: "71-43-2" },
    { id: "toluene", name: "toluene", cas: "108-88-3" },
  ],
  units: [
    { id: "FEED-1", type: "feed" },
    { id: "F-1", type: "flash", specs: { pressure: { value: 101325, unit: "Pa" } } },
    { id: "SP-1", type: "splitter" },
  ],
  streams: [{ id: "S1", from: { unit: "FEED-1", port: "out" }, to: { unit: "F-1", port: "in" } }],
});

/** Shows the live document so tests can assert on it. */
function DocProbe() {
  const { doc } = useFlowsheet();
  return <pre data-testid="doc">{JSON.stringify(doc)}</pre>;
}
const currentDoc = () => JSON.parse(screen.getByTestId("doc").textContent ?? "{}") as Flowsheet;

describe("flowsheet page", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("adds units from the palette and shows unsupported ones as coming later", async () => {
    const user = userEvent.setup();
    renderWithApp(<><FlowsheetPage /><DocProbe /></>);
    const palette = screen.getByRole("complementary", { name: "Units" });
    await user.click(within(palette).getByRole("button", { name: /^Feed$/ }));
    await user.click(within(palette).getByRole("button", { name: /^Flash$/ }));
    expect(currentDoc().units.map((u) => u.id)).toEqual(["FEED-1", "F-1"]);
    expect(within(palette).getByRole("button", { name: /Pump/ })).toBeDisabled();
    await waitFor(() => expect(screen.getByText("F-1")).toBeInTheDocument());
  });
});

describe("side panel", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("edits flash specs as exclusive choices", async () => {
    const user = userEvent.setup();
    renderWithApp(<><SidePanel selection={{ kind: "unit", id: "F-1" }} issues={null} onDeleted={() => {}} /><DocProbe /></>, flashDrum());
    const thermal = screen.getByRole("group", { name: "Outlet condition" });
    await user.type(within(thermal).getByRole("textbox", { name: "Temperature" }), "368,15{Enter}");
    expect(currentDoc().units[1].specs).toEqual({
      pressure: { value: 101325, unit: "Pa" }, temperature: { value: 368.15, unit: "K" } });
    await user.click(within(thermal).getByRole("radio", { name: "Duty" }));
    expect(currentDoc().units[1].specs?.temperature).toBeUndefined();
    await user.type(within(thermal).getByRole("textbox", { name: "Duty" }), "0{Enter}");
    expect(currentDoc().units[1].specs?.duty).toEqual({ value: 0, unit: "W" });
  });

  it("edits feed conditions and normalizes the composition", async () => {
    const user = userEvent.setup();
    renderWithApp(<><SidePanel selection={{ kind: "unit", id: "FEED-1" }} issues={null} onDeleted={() => {}} /><DocProbe /></>, flashDrum());
    const feed = screen.getByRole("group", { name: /Feed conditions/ });
    await user.type(within(feed).getByRole("textbox", { name: "Temperature" }), "350{Enter}");
    await user.type(within(feed).getByRole("textbox", { name: "Pressure" }), "101325{Enter}");
    await user.type(within(feed).getByRole("textbox", { name: "Molar flow" }), "100{Enter}");
    await user.type(within(feed).getByRole("textbox", { name: "benzene" }), "1{Enter}");
    await user.type(within(feed).getByRole("textbox", { name: "toluene" }), "3{Enter}");
    expect(within(feed).getByText("Sum: 4.0000")).toBeInTheDocument();
    await user.click(within(feed).getByRole("button", { name: "Normalize" }));
    expect(currentDoc().streams[0].state).toEqual({
      temperature: { value: 350, unit: "K" },
      pressure: { value: 101325, unit: "Pa" },
      molar_flow: { value: 100, unit: "mol/s" },
      mole_fractions: { benzene: 0.25, toluene: 0.75 },
    });
  });

  it("shows translated engine issues for the selected unit, including its feed stream", async () => {
    const issues: EngineIssue[] = [
      { severity: "error", code: "missing_spec", message_key: "issues.missing_spec",
        target: { kind: "stream", id: "S1" }, params: { target: "S1", spec: "temperature / vapor_fraction" } },
      { severity: "error", code: "unconnected_port", message_key: "issues.unconnected_port",
        target: { kind: "unit", id: "F-1" }, params: { target: "F-1", port: "vapor" } },
    ];
    renderWithApp(<SidePanel selection={{ kind: "unit", id: "FEED-1" }} issues={issues} onDeleted={() => {}} />, flashDrum(),
      () => fakeEngine(() => issues));
    expect(screen.getByText("S1: Temperature / Vapour fraction is missing.")).toBeInTheDocument();
    expect(screen.queryByText(/port "vapor"/)).toBeNull();
  });

  it("asks to connect splitter outlets before fractions", () => {
    renderWithApp(<SidePanel selection={{ kind: "unit", id: "SP-1" }} issues={[]} onDeleted={() => {}} />, flashDrum());
    expect(screen.getByText("Connect at least two outlets.")).toBeInTheDocument();
    expect(screen.getByText("Nothing missing.")).toBeInTheDocument();
  });
});
