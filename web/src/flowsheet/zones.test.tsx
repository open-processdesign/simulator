import { beforeEach, describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import i18n from "@/i18n";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { renderWithApp } from "@/test/render";
import { SidePanel } from "./SidePanel";
import { useFlowsheet } from "@/state/FlowsheetProvider";

function Probe() {
  const { doc } = useFlowsheet();
  return <output data-testid="zones">{String(doc.units[0].options?.zones ?? "default")}</output>;
}

describe("heat exchanger zones", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("stores an integer zone count and clears it back to the default", async () => {
    const user = userEvent.setup();
    const doc: Flowsheet = { ...emptyFlowsheet("t"), units: [{ id: "E-1", type: "heat_exchanger", specs: {} }] };
    renderWithApp(<><SidePanel selection={{ kind: "unit", id: "E-1" }} issues={null} onDeleted={() => {}} /><Probe /></>, doc);
    const field = screen.getByRole("spinbutton", { name: "Zones" });
    expect(field).toHaveAttribute("placeholder", "10");
    await user.type(field, "25");
    expect(screen.getByTestId("zones")).toHaveTextContent("25");
    await user.clear(field);
    expect(screen.getByTestId("zones")).toHaveTextContent("default");
    expect(screen.getByText(/bubble and dew points/)).toBeInTheDocument();
  });
});
