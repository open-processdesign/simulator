import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { renderWithApp } from "@/test/render";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { SidePanel } from "./SidePanel";

function Probe() {
  const { doc } = useFlowsheet();
  return <output data-testid="options">{JSON.stringify(doc.units[0].options)}</output>;
}

describe("equilibrium reactor editor", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("sets the liquid phase and a ln K correlation while keeping the stoichiometry", async () => {
    const user = userEvent.setup();
    const doc: Flowsheet = {
      ...emptyFlowsheet("t"),
      components: [{ id: "ib", name: "isobutene", cas: "115-11-7" }, { id: "mtbe", name: "MTBE", cas: "1634-04-4" }],
      units: [{ id: "R-1", type: "equilibrium_reactor", specs: {}, options: { reactions: [{ stoichiometry: { ib: -1, mtbe: 1 } }] } }],
    };
    renderWithApp(<><SidePanel selection={{ kind: "unit", id: "R-1" }} issues={null} onDeleted={() => {}} /><Probe /></>, doc);
    await user.selectOptions(screen.getByRole("combobox", { name: "Reacting phase" }), "liquid");
    expect(screen.getByText(/activities x·γ relative to the pure liquid/)).toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "Equilibrium constant" }), "correlation");
    const b = screen.getByRole("textbox", { name: "b [K]" });
    await user.type(b, "4703{Enter}");
    const a = screen.getByRole("textbox", { name: "a" });
    await user.clear(a);
    await user.type(a, "-10,3{Enter}");
    const options = JSON.parse(screen.getByTestId("options").textContent ?? "{}");
    expect(options.phase).toBe("liquid");
    expect(options.reactions[0]).toEqual({ stoichiometry: { ib: -1, mtbe: 1 }, ln_k: { a: -10.3, b: 4703 } });
  });
});
