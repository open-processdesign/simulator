import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import type { EngineClient } from "@/engine/client";
import type { EngineResult } from "@/engine/bootstrap";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { fakeEngine, renderWithApp } from "@/test/render";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { useSelection } from "@/state/SelectionProvider";
import { ResultsPage } from "./ResultsPage";
import { RunPage } from "./RunPage";

const doc: Flowsheet = {
  ...emptyFlowsheet("t"),
  components: [{ id: "benzene", name: "benzene", cas: "71-43-2" }, { id: "toluene", name: "toluene", cas: "108-88-3" }],
  units: [{ id: "FEED-1", type: "feed" }, { id: "F-1", type: "flash" }, { id: "PROD-1", type: "product" }],
  streams: [
    { id: "S1", from: { unit: "FEED-1", port: "out" }, to: { unit: "F-1", port: "in" } },
    { id: "S2", from: { unit: "F-1", port: "vapor" }, to: { unit: "PROD-1", port: "in" } },
  ],
};

// Numbers below only exercise the display; real numbers always come from the engine.
const solved: EngineResult = {
  converged: true, engine: "reference", engine_version: "opd-reference 0.1 (thermo 0.6.1)",
  document: { results: {
    engine: "reference", engine_version: "opd-reference 0.1 (thermo 0.6.1)", converged: true,
    streams: {
      S1: { temperature: { value: 350, unit: "K" }, pressure: { value: 101325, unit: "Pa" }, molar_flow: { value: 100, unit: "mol/s" },
        vapor_fraction: { value: 0, unit: "1" }, mole_fractions: { benzene: 0.5, toluene: 0.5 } },
      S2: { temperature: { value: 368.15, unit: "K" }, pressure: { value: 101325, unit: "Pa" }, molar_flow: { value: 43.76, unit: "mol/s" },
        vapor_fraction: { value: 1, unit: "1" }, mole_fractions: { benzene: 0.6211, toluene: 0.3789 } },
    },
    units: { "F-1": { duty: { value: 1653369, unit: "W" }, vapor_fraction: { value: 0.4376, unit: "1" } } },
  } },
  issues: [{ severity: "warning", code: "missing_binary_parameter", message_key: "issues.missing_binary_parameter",
    target: { kind: "thermo", id: null }, params: { i: "benzene", j: "toluene" } }],
};

const engineWith = (result: EngineResult): (() => EngineClient) => () => ({ ...fakeEngine(), simulate: async () => ({ result, ms: 12 }) });

function Probe() {
  const { selection } = useSelection();
  const { dispatch } = useFlowsheet();
  return (
    <>
      <span data-testid="selection">{selection ? `${selection.kind}:${selection.id}` : ""}</span>
      <button onClick={() => dispatch({ type: "set_label", id: "F-1", label: "changed" })}>edit</button>
    </>
  );
}

describe("run and results", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    window.location.hash = "";
  });

  it("runs, shows the stream table, unit results and messages; marks results stale after an edit", async () => {
    const user = userEvent.setup();
    renderWithApp(<><ResultsPage /><Probe /></>, doc, engineWith(solved));
    expect(screen.getByText(/Stream tables and unit results appear here/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Run" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText("Solved in 12 ms with opd-reference 0.1 (thermo 0.6.1).")).toBeInTheDocument();
    expect(window.location.hash).toBe("#/results");
    const table = screen.getByRole("table", { name: "Stream table" });
    const row = (label: string) => within(table).getByRole("row", { name: new RegExp(`^${label}`) });
    expect(within(row("Temperature")).getAllByRole("cell").map((c) => c.textContent)).toEqual(["K", "350.00", "368.15"]);
    expect(within(row("x benzene")).getAllByRole("cell").map((c) => c.textContent)).toEqual(["–", "0.5000", "0.6211"]);
    expect(screen.getByText("No binary parameter for benzene–toluene; using k_ij = 0.")).toBeInTheDocument();
    expect(screen.getByText("1,653,369")).toBeInTheDocument(); // flash duty in W

    await user.click(screen.getByRole("button", { name: "edit" }));
    expect(screen.getByText(/The flowsheet changed after this run/)).toBeInTheDocument();

    await user.click(within(table).getByRole("button", { name: "S2" }));
    expect(screen.getByTestId("selection")).toHaveTextContent("stream:S2");
    expect(window.location.hash).toBe("#/flowsheet");
  });

  it("shows errors of a failed run with links to the canvas", async () => {
    const user = userEvent.setup();
    const failed: EngineResult = { ...solved, converged: false, document: {}, issues: [
      { severity: "error", code: "calculation_failed", message_key: "issues.calculation_failed",
        target: { kind: "unit", id: "F-1" }, params: { target: "F-1", detail: "no convergence" } }] };
    renderWithApp(<><ResultsPage /><Probe /></>, doc, engineWith(failed));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run" }));
    expect(await screen.findByText(/could not be solved/)).toBeInTheDocument();
    expect(screen.getByText("F-1: the calculation did not converge (no convergence).")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show F-1" }));
    expect(screen.getByTestId("selection")).toHaveTextContent("unit:F-1");
  });

  it("run page lists what is missing", async () => {
    const engine = () => fakeEngine(() => [{ severity: "error", code: "missing_spec", message_key: "issues.missing_spec",
      target: { kind: "unit", id: "F-1" }, params: { target: "F-1", spec: "pressure / pressure_drop" } }]);
    renderWithApp(<RunPage />, doc, engine);
    expect(await screen.findByText("Complete these 1 inputs first:")).toBeInTheDocument();
    expect(screen.getByText("F-1: Pressure / Pressure drop is missing.")).toBeInTheDocument();
  });
});
