import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { renderWithApp } from "@/test/render";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { UnitSetProvider } from "@/units/UnitSetProvider";
import { SidePanel } from "./SidePanel";

function Probe() {
  const { doc } = useFlowsheet();
  return <output data-testid="geometry">{JSON.stringify(doc.units[0].options?.geometry ?? null)}</output>;
}

describe("shell-and-tube geometry editor", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("switches geometry on with defaults, edits fields in the unit set and switches it off", async () => {
    const user = userEvent.setup();
    const doc: Flowsheet = { ...emptyFlowsheet("t"), units: [{ id: "E-1", type: "heat_exchanger", specs: {} }] };
    renderWithApp(
      <UnitSetProvider initial="METRIC"><SidePanel selection={{ kind: "unit", id: "E-1" }} issues={null} onDeleted={() => {}} /><Probe /></UnitSetProvider>, doc);
    const geometry = () => JSON.parse(screen.getByTestId("geometry").textContent ?? "null");
    expect(geometry()).toBeNull();
    await user.click(screen.getByRole("checkbox", { name: "Use a shell-and-tube geometry" }));
    expect(geometry().tube_count).toBe(160);
    // Diameters are shown in mm in the metric set and stored in metres.
    const od = screen.getByRole("textbox", { name: "Tube outer diameter" });
    expect(od).toHaveValue("19");
    await user.clear(od);
    await user.type(od, "25,4{Enter}");
    expect(geometry().tube_outer_diameter).toBeCloseTo(0.0254, 10);
    await user.selectOptions(screen.getByRole("combobox", { name: "Tube passes" }), "4");
    await user.selectOptions(screen.getByRole("combobox", { name: "Fluid in the tubes" }), "hot");
    expect(geometry()).toMatchObject({ tube_passes: 4, tube_side: "hot" });
    await user.click(screen.getByRole("checkbox", { name: "Use a shell-and-tube geometry" }));
    expect(geometry()).toBeNull();
  });
});
